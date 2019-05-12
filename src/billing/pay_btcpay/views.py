from btcpay import BTCPayClient
from django.conf import settings
from django.http import HttpResponseRedirect

from billing.pay_btcpay.models import BTCPayInvoice


def start_payment(transaction_id, amount):
    client = BTCPayClient(
            host=settings.ZENAIDA_BTCPAY_HOST,
            pem=settings.ZENAIDA_BTCPAY_CLIENT_PRIVATE_KEY,
            tokens={"merchant": settings.ZENAIDA_BTCPAY_MERCHANT}
        )

    btcpay_invoice = client.create_invoice({"price": 1, "currency": "USD"})

    BTCPayInvoice.invoices.create(
        transaction_id=transaction_id,
        invoice_id=btcpay_invoice.get('id'),
        status=btcpay_invoice.get('status'),
        amount=amount
    )
    return HttpResponseRedirect(btcpay_invoice.get("url"))
