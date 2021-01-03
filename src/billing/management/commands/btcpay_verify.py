import logging
import time

from btcpay import BTCPayClient

from django.conf import settings
from django.core.management.base import BaseCommand

from django.utils import timezone

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
                time.sleep(60)
                continue

            logger.info('check payments at %r', timezone.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Check status of all incomplete invoices.
            incomplete_invoices = BTCPayInvoice.invoices.filter(finished_at=None)

            for invoice in incomplete_invoices:
                try:
                    btcpay_resp = client.get_invoice(invoice.invoice_id)
                except:
                    logger.exception("BTCPay server connection problem while checking invoice payment status.")
                    break

                # If status is new, there is not any update yet on BTCPay server, so move to the next invoice.
                if btcpay_resp.get('status') == 'new':
                    logger.debug(f'active btcpay invoice: {invoice}')
                    continue

                # If invoice is paid, process the payment in the database as paid.
                # Else, payment is not done, so decline the payment in the database.
                if btcpay_resp['btcPaid'] >= btcpay_resp['btcPrice']:
                    logger.debug(f'paid btcpay invoice: {invoice}')
                    payment_status = 'processed'
                    btcpay_invoice_status = 'paid'
                else:
                    logger.debug(f'expired btcpay invoice: {invoice}')
                    payment_status = 'declined'
                    btcpay_invoice_status = 'expired'

                if not payments.finish_payment(transaction_id=invoice.transaction_id, status=payment_status):
                    logger.critical(f'payment failed to be completed, transaction_id={invoice.transaction_id}')
                    continue

                invoice.status = btcpay_invoice_status
                invoice.finished_at = timezone.now()
                invoice.save()
                logger.info(f'payment is {payment_status} because it is {btcpay_invoice_status}, '
                            f'transaction_id={invoice.transaction_id}')

            time.sleep(60)
