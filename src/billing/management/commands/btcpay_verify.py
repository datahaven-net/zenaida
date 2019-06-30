import logging
import time
import datetime

from btcpay import BTCPayClient
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from base.sms import SMSSender
from billing import payments

from billing.pay_btcpay.models import BTCPayInvoice

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Starts background process to check BTCPay statuses'

    def handle(self, *args, **options):
        client = BTCPayClient(
            host=settings.ZENAIDA_BTCPAY_HOST,
            pem=settings.ZENAIDA_BTCPAY_CLIENT_PRIVATE_KEY,
            tokens={"merchant": settings.ZENAIDA_BTCPAY_MERCHANT}
        )

        while True:
            time_threshold = timezone.now() - datetime.timedelta(hours=1)

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
                    logger.critical(f'Payment failed to be declined, transaction_id={expired_invoice.transaction_id}')
                    continue
                expired_invoice.status = 'expired'
                expired_invoice.finished_at = timezone.now()
                expired_invoice.save()
                logger.info(f'Payment declined because of expiration, transaction_id={expired_invoice.transaction_id}')
                
            btcpay_active_invoices = BTCPayInvoice.invoices.filter(started_at__gte=time_threshold)
            for invoice in btcpay_active_invoices:
                logger.debug('active: %r' % invoice)
                if invoice.status != 'paid':
                    try:
                        btcpay_resp = client.get_invoice(invoice.invoice_id)
                    except:
                        if not cache.get("bruteforce_protection_sms"):
                            SMSSender(
                                text_message="There is a problem with BTCPay Server. Please check the server status."
                            ).send_sms()
                            cache.set("bruteforce_protection_sms", True, 60 * 60)
                        break
                    if btcpay_resp['btcPaid'] == btcpay_resp['btcPrice']:
                        if not payments.finish_payment(
                            transaction_id=invoice.transaction_id,
                            status='processed',
                        ):
                            logger.critical(f'Payment failed to be completed, transaction_id={invoice.transaction_id}')
                            continue
                        invoice.status = 'paid'
                        invoice.finished_at = timezone.now()
                        invoice.save()
                        logger.info(f'Payment succeed, transaction_id={invoice.transaction_id}')

            time.sleep(5 * 60)
