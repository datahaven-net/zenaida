import logging
import time
import datetime

from btcpay import BTCPayClient

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from django.utils import timezone

from base.sms import SMSSender
from base.email import send_email

from billing import payments
from billing.pay_btcpay.models import BTCPayInvoice

from zen import zusers

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Starts background process to check & sync invoices with BTCPay server'

    def handle(self, *args, **options):
        client = BTCPayClient(
            host=settings.ZENAIDA_BTCPAY_HOST,
            pem=settings.ZENAIDA_BTCPAY_CLIENT_PRIVATE_KEY,
            tokens={"merchant": settings.ZENAIDA_BTCPAY_MERCHANT}
        )

        # first check if we miss some completed invoices
        # if some invoices are missed - we must catch up with BTCPay server
        latest_known_invoice = BTCPayInvoice.invoices.latest('started_at')
        if latest_known_invoice:
            while True:
                # before doing any requests, make sure connection is alive
                try:
                    client.get_rate("USD")
                except:
                    logger.exception("BTCPay server connection problem while getting rates.")
                    self._send_sms_and_email_alert()
                    time.sleep(60)
                    continue

                # request list of invoices from BTCPay server chunk by chunk until we found latest known invoice
                offset = 0
                limit_one_iteration = 10
                while True:
                    try:
                        several_invoices = client.get_invoices(limit=limit_one_iteration, offset=offset)
                    except:
                        logger.exception("BTCPay server connection problem while checking recent invoices.")
                        self._send_sms_and_email_alert()
                        break
                    if not several_invoices:
                        logger.critical('BTCPay server returned empty list of invoices, latest invoice was not found')
                        break
                    found_latest_invoice = False
                    for invoice in several_invoices:
                        order_id = invoice.get('orderId')
                        invoice_id = invoice.get('id')
                        if not invoice_id:
                            logger.critical('wrong invoice, no ID found in payload: %r', invoice)
                            continue
                        invoice_status = invoice.get('status')
                        try:
                            invoice_price = float(invoice.get('price', 0.0))
                            invoice_btc_paid = float(invoice.get('btcPaid', 0.0))
                            invoice_btc_price = float(invoice.get('btcPrice', 0.0))
                        except:
                            logger.exception('wrong invoice, invalid "btcPrice", "btcPaid" or "price" field: %r', invoice)
                            continue
                        if order_id and order_id == latest_known_invoice.transaction_id:
                            logger.info('in sync, found latest invoice by transaction_id : %r', latest_known_invoice)
                            found_latest_invoice = True
                            break
                        if invoice_id == latest_known_invoice.invoice_id:
                            logger.info('in sync, found latest invoice %r by invoice_id : %r', invoice_id, latest_known_invoice)
                            found_latest_invoice = True
                            break
                        item_desc = invoice.get('itemDesc')
                        if item_desc and not item_desc.count(settings.SITE_BASE_URL):
                            # skip invoice if it was started from non-prod Zenaida server
                            logger.debug('skip invoice %r because started by another server: %r', invoice_id, item_desc)
                            continue
                        buyer_info = invoice.get('buyer', {})
                        if not buyer_info:
                            logger.debug('skip invoice %r, no buyer info found in payload', invoice_id)
                            continue
                        buyer_email = buyer_info.get('email')
                        if not buyer_email:
                            logger.debug('skip invoice %r, no buyer email found in payload', invoice_id)
                            continue
                        known_account = zusers.find_account(buyer_email)
                        if not known_account:
                            logger.critical('critical issue, found valid invoice %r, but user account not exist in local DB : %r', invoice_id, buyer_email)
                            continue
                        known_invoice = BTCPayInvoice.invoices.filter(invoice_id=invoice_id).first()
                        if known_invoice:
                            logger.critical('found known invoice %r, but somehow it is not latest', invoice_id)
                            continue
                        # now we know for sure this invoice is correct, but does not exist in local DB
                        # first create a new payment object for that user
                        new_payment = payments.start_payment(
                            owner=known_account,
                            amount=invoice_price,
                            payment_method='pay_btcpay',
                        )
                        # also create corresponding BTCPay invoice record
                        new_invoice = BTCPayInvoice.invoices.create(
                            transaction_id=new_payment.transaction_id,
                            invoice_id=invoice_id,
                            status=invoice_status,
                            amount=invoice_price,
                        )
                        # if that payment already completed on BTCPay server, we must process it
                        if invoice_btc_paid >= invoice_btc_price:
                            if invoice_btc_paid > invoice_btc_price:
                                logger.warn('found over-paid invoice: %r', new_invoice)
                            if not payments.finish_payment(
                                transaction_id=new_invoice.transaction_id,
                                status='processed',
                            ):
                                logger.critical(f'payment failed to be completed, transaction_id={new_invoice.transaction_id}')
                                continue
                            new_invoice.status = 'paid'
                            new_invoice.finished_at = timezone.now()
                            new_invoice.save()
                            logger.info(f'payment succeed, transaction_id={new_invoice.transaction_id}')

                    if found_latest_invoice:
                        logger.info('found latest invoice in BTCPay server response, continue')
                        break

                    # take next chunk of invoices to catch up
                    offset += limit_one_iteration
                    logger.debug('going to read next chunk of invoices from BTCPay server, offset=%r', offset)

        # run main loop : every X seconds check all known pending invoices.
        # when BTCPay server reports invoice is paid - process it and accept payment.
        while True:
            # before doing any requests, make sure connection is alive
            try:
                client.get_rate("USD")
            except:
                logger.exception("BTCPay server connection problem while getting rates.")
                self._send_sms_and_email_alert()
                time.sleep(60)
                continue

            logger.info('check payments at %r', timezone.now().strftime("%Y-%m-%d %H:%M:%S"))
            time_threshold = timezone.now() - datetime.timedelta(hours=1)

            # select invoices older than 1 hour and expire them - mark payment as declined
            btcpay_expired_invoices = BTCPayInvoice.invoices.filter(started_at__lt=time_threshold, finished_at=None)
            for expired_invoice in btcpay_expired_invoices:
                logger.debug('expired: %r' % expired_invoice)
                expired_payment_object = payments.by_transaction_id(expired_invoice.transaction_id)
                if not expired_payment_object:
                    continue
                if not payments.finish_payment(
                    transaction_id=expired_invoice.transaction_id,
                    status='declined',
                ):
                    logger.critical(f'payment failed to be declined, transaction_id={expired_invoice.transaction_id}')
                    continue
                expired_invoice.status = 'expired'
                expired_invoice.finished_at = timezone.now()
                expired_invoice.save()
                logger.info(f'payment declined because of expiration, transaction_id={expired_invoice.transaction_id}')

            # finally select all known active invoices and check if they are paid on BTCPay server
            btcpay_active_invoices = BTCPayInvoice.invoices.filter(started_at__gte=time_threshold)
            for invoice in btcpay_active_invoices:
                logger.debug('active: %r' % invoice)
                if invoice.status != 'paid':
                    try:
                        btcpay_resp = client.get_invoice(invoice.invoice_id)
                    except:
                        logger.exception("BTCPay server connection problem while checking invoice payment status.")
                        self._send_sms_and_email_alert()
                        break
                    try:
                        btc_paid = float(btcpay_resp.get('btcPaid', '0.0'))
                        btc_price = float(btcpay_resp.get('btcPrice', '0.0'))
                    except ValueError:
                        logger.exception('bad invoice response, wrong btcPaid or btcPrice field: %r', btcpay_resp)
                        continue
                    if not btc_paid:
                        continue
                    if btc_paid >= btc_price:
                        if btc_paid > btc_price:
                            logger.warn('found over-paid invoice: %r', invoice)
                        if not payments.finish_payment(
                            transaction_id=invoice.transaction_id,
                            status='processed',
                        ):
                            logger.critical(f'payment failed to be completed, transaction_id={invoice.transaction_id}')
                            continue
                        invoice.status = 'paid'
                        invoice.finished_at = timezone.now()
                        invoice.save()
                        logger.info(f'payment succeed, transaction_id={invoice.transaction_id}')

            # wait X seconds and re-check pending invoices again
            time.sleep(10)

    @staticmethod
    def _send_sms_and_email_alert():
        if not cache.get("bruteforce_protection_sms"):
            SMSSender(
                text_message="There is a problem with BTCPay Server. Please check the server status."
            ).send_sms()
            cache.set("bruteforce_protection_sms", True, 60 * 60)
        if not cache.get("bruteforce_protection_email"):
            for email_address in settings.ALERT_EMAIL_RECIPIENTS:
                send_email(
                    subject='BTCPay Server connectivity issue',
                    text_content='There is a problem with BTCPay Server. Please check the server status.',
                    from_email=settings.EMAIL_ADMIN,
                    to_email=email_address,
                )
            cache.set("bruteforce_protection_email", True, 60 * 60)
