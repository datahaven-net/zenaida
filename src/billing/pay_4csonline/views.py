import logging

from django import urls
from django import shortcuts
from django.core import exceptions
from django.conf import settings

from billing.models.payment import Payment


def start_payment(request, transaction_id):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    return shortcuts.render(request, 'billing/4csonline/start_payment.html', {
        'transaction_id': transaction_id,
    })


def process_payment(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    payment_object = shortcuts.get_object_or_404(Payment, transaction_id=request.GET.get('transaction_id', ''))
    if payment_object.owner != request.user:
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: payment owner is not matching to request')
        raise exceptions.SuspiciousOperation()
    return shortcuts.render(request, 'billing/4csonline/merchant_form.html', {
        'company_name': 'DataHaven.Net Ltd',
        'price': '{}.00'.format(payment_object.amount),
        'merch_id': settings.BILLING_4CSONLINE_MERCHANT_ID,
        'merch_link': settings.BILLING_4CSONLINE_MERCHANT_LINK,
        'invoice': payment_object.transaction_id,
        'tran_id': payment_object.transaction_id,
        'url_approved': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
        'url_other': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
    })


def verify_payment(request):
    if not request.user.is_authenticated:
        logging.critical('Invalid request, payment verification will raise SuspiciousOperation: request user is not authenticated')
        raise exceptions.SuspiciousOperation()
    payment_object = shortcuts.get_object_or_404(Payment, transaction_id=request.GET.get('invoice', ''))
    if payment_object.owner != request.user:
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: payment owner is not matching to request')
        raise exceptions.SuspiciousOperation()
    if settings.BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION:
        return shortcuts.render(request, 'billing/4csonline/success_payment.html', {
        })
