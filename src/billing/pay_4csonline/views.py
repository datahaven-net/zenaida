from django import shortcuts

from django.conf import settings

from billing.models.payment import Payment


def start_payment(request, transaction_id):
    return shortcuts.render(request, 'billing/4csonline/start_payment.html', {
        'invoice': transaction_id,
        'tran_id': transaction_id,
    })


def process_payment(request):
    payment_object = shortcuts.get_object_or_404(Payment, transaction_id=request.GET.get('invoice', ''))
    return shortcuts.render(request, 'billing/4csonline/merchant_form.html', {
        'price': '{}.00'.format(payment_object.amount),
        'merch_id': settings.BILLING_4CSONLINE_MERCHANT_ID,
        'merch_link': settings.BILLING_4CSONLINE_MERCHANT_LINK,
        'invoice': payment_object.transaction_id,
        'tran_id': payment_object.transaction_id,
    })


def verify_payment(request):
    payment_object = shortcuts.get_object_or_404(Payment, transaction_id=request.GET.get('invoice', ''))
    return shortcuts.render(request, 'billing/4csonline/success_payment.html', {
    })
