import logging

import btcpay
from django import shortcuts
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.views import View

from billing import orders as billing_orders
from billing.pay_btcpay.models import BTCPayInvoice

logger = logging.getLogger(__name__)


class ProcessPaymentView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        transaction_id = kwargs.get('transaction_id')
        amount = request.POST['amount']
        try:
            client = btcpay.BTCPayClient(
                host=settings.ZENAIDA_BTCPAY_HOST,
                pem=settings.ZENAIDA_BTCPAY_CLIENT_PRIVATE_KEY,
                tokens={
                    "merchant": settings.ZENAIDA_BTCPAY_MERCHANT,
                },
            )

            btcpay_invoice = client.create_invoice(
                payload={
                    "price": amount,
                    "currency": "USD",
                    "orderId": transaction_id,
                    "notificationEmail": request.user.email,
                    "physical": False,
                    "itemDesc": "BitCoin payment on %s" % settings.SITE_BASE_URL,
                    "buyer": {
                        "name": request.user.profile.person_name,
                        "address1": request.user.profile.address_street,
                        "address2": "",
                        "zip": request.user.profile.address_postal_code,
                        "city": request.user.profile.address_city,
                        "state": request.user.profile.address_province,
                        "country": request.user.profile.address_country,
                        "phone": request.user.profile.contact_voice,
                        "notify": True,
                        "email": request.user.email,
                    },
                },
            )

            BTCPayInvoice.invoices.create(
                transaction_id=transaction_id,
                invoice_id=btcpay_invoice.get('id'),
                status=btcpay_invoice.get('status'),
                amount=amount,
            )
        except Exception as exc:
            logger.exception(exc)
            messages.error(self.request, "There is a technical problem with BitCoin payments at this moment, please try again later")
            return shortcuts.redirect('billing_new_payment')

        return HttpResponseRedirect(btcpay_invoice.get("url"))


class RedirectPaymentView(View):
    def dispatch(self, request, *args, **kwargs):
        # If there is any order which needs to be completed, redirect user to that order to complete the order.
        # Otherwise, go back to the payments overview.
        started_orders = billing_orders.list_orders(
            owner=self.request.user,
            exclude_cancelled=True,
            include_statuses=['started']
        )
        if started_orders:
            messages.warning(self.request, 'You have an ongoing order. Please click the "Confirm" button '
                                           'to complete the order.')
            return shortcuts.redirect('billing_order_details', order_id=started_orders[0].id)
        return shortcuts.redirect('billing_payments')
