import logging

from django import urls
from django import shortcuts
from django.utils import timezone
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

    if payment_object.finished_at:
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: payment transaction already finished')
        raise exceptions.SuspiciousOperation()

    return shortcuts.render(request, 'billing/4csonline/merchant_form.html', {
        'company_name': 'DataHaven.Net Ltd',
        'price': '{}.00'.format(int(payment_object.amount)),
        'merch_id': settings.BILLING_4CSONLINE_MERCHANT_ID,
        'merch_link': settings.BILLING_4CSONLINE_MERCHANT_LINK,
        'invoice': payment_object.transaction_id,
        'tran_id': payment_object.transaction_id,
        'url_approved': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
        'url_other': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
    })


def verify_payment(request):
    payment_object = shortcuts.get_object_or_404(Payment, transaction_id=request.GET['invoice'])

    if payment_object.finished_at:
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: payment transaction already finished')
        raise exceptions.SuspiciousOperation()

    if payment_object.amount != float(request.GET['amt'].replace(',', '')):
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: transaction amount not matching with existing record')
        raise exceptions.SuspiciousOperation()

    if not settings.BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION:
        if request.GET.get('result') != 'pass':
            payment_object.status = 'failed'
            payment_object.finished_at = timezone.now()
            payment_object.merchant_reference = request.GET['ref']
            payment_object.save()
            message = 'transaction was declined'
            if request.GET.get('err') == 'INCOMPLETE':
                message = 'transaction was cancelled'
            return shortcuts.render(request, 'billing/4csonline/failed_payment.html', {
                'message': message,
            })

    # TODO: add verification request towards merchant back-end 
    payment_object.status = 'processed'
    payment_object.finished_at = timezone.now()
    payment_object.merchant_reference = request.GET['ref']
    payment_object.save()

    payment_object.owner.balance += payment_object.amount
    payment_object.owner.save()

    return shortcuts.render(request, 'billing/4csonline/success_payment.html')
