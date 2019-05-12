import datetime

from btcpay import BTCPayClient
from django.conf import settings
from django.core.management.base import BaseCommand

from billing.pay_btcpay.models import BTCPayInvoice


class Command(BaseCommand):

    help = 'Starts background process to check BTCPay statuses'

    def handle(self, *args, **options):
        client = BTCPayClient(
            host=settings.ZENAIDA_BTCPAY_HOST,
            pem=settings.ZENAIDA_BTCPAY_CLIENT_PRIVATE_KEY,
            tokens={"merchant": settings.ZENAIDA_BTCPAY_MERCHANT}
        )

        while True:
            time_threshold = datetime.datetime.now() - datetime.timedelta(hours=1)
            btcpay_invoices = BTCPayInvoice.invoices.filter(started_at__gte=time_threshold)

            for invoice in btcpay_invoices:
                if invoice.status != 'paid':
                    btcpay_resp = client.get_invoice(invoice.invoice_id)
                    if btcpay_resp['btcPaid'] == btcpay_resp['btcPrice']:
                        invoice.status = 'paid'
                        invoice.save()
                # TODO: Update main payment table
                # TODO: Add balance to the user.
