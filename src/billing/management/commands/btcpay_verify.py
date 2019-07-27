import logging
import time

from btcpay import BTCPayClient

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from django.utils import timezone

from base.sms import SMSSender
from base.email import send_email

from billing import payments
from billing.pay_btcpay.models import BTCPayInvoice

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Starts background process to check & sync invoices with BTCPay server'

    def handle(self, *args, **options):
        client = BTCPayClient(
            host=settings.ZENAIDA_BTCPAY_HOST,
            pem=settings.ZENAIDA_BTCPAY_CLIENT_PRIVATE_KEY,
            tokens={"merchant": settings.ZENAIDA_BTCPAY_MERCHANT}
        )

        while True:
            # Check if BTCPay server is up and running.
            try:
                client.get_rate("USD")
            except:
                logger.exception("BTCPay server connection problem while getting rates.")
                self._send_sms_and_email_alert()
                time.sleep(60)
                continue

            logger.info('Check payments at %r', timezone.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Check status of all incomplete invoices.
            incomplete_invoices = BTCPayInvoice.invoices.filter(finished_at=None)

            for invoice in incomplete_invoices:
                try:
                    btcpay_resp = client.get_invoice(invoice.invoice_id)
                except:
                    logger.exception("BTCPay server connection problem while checking invoice payment status.")
                    self._send_sms_and_email_alert()
                    break

                # If status is new, there is not any update yet on BTCPay server, so move to the next invoice.
                if btcpay_resp.get('status') == 'new':
                    logger.debug(f'active btcpay invoice: {invoice}')
                    continue

                # If invoice is paid, process the payment in the database as paid.
                # Else, payment is not done, so decline the payment in the database.
                if btcpay_resp['btcPaid'] == btcpay_resp['btcPrice']:
                    logger.debug(f'paid btcpay invoice: {invoice}')
                    payment_status = 'processed'
                    btcpay_invoice_status = 'paid'
                else:
                    logger.debug(f'expired btcpay invoice: {invoice}')
                    payment_status = 'declined'
                    btcpay_invoice_status = 'expired'

                if not payments.finish_payment(transaction_id=invoice.transaction_id, status=payment_status):
                    logger.critical(f'Payment failed to be completed, transaction_id={invoice.transaction_id}')
                    continue

                invoice.status = btcpay_invoice_status
                invoice.finished_at = timezone.now()
                invoice.save()
                logger.info(f'Payment is {payment_status} because it is {btcpay_invoice_status}, '
                            f'transaction_id={invoice.transaction_id}')

            time.sleep(60)

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
