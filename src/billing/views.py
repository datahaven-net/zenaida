import random
import string

from django import shortcuts

from django.conf import settings

from billing import forms
from billing.models.payment import Payment


def generate_transaction_id(size=10, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def new_payment(request):
    if request.method != 'POST':
        form = forms.NewPaymentForm()
        return shortcuts.render(request, 'billing/new_payment.html', {
            'form': form,
        })
    form = forms.NewPaymentForm(request.POST)
    if not form.is_valid():
        return shortcuts.render(request, 'billing/new_payment.html', {
            'form': form,
        })

    new_transaction_id = generate_transaction_id()
    while Payment.payments.filter(transaction_id=new_transaction_id).exists():
        new_transaction_id = generate_transaction_id()

    new_payment = Payment.payments.create(
        owner=request.user,
        amount=form.cleaned_data['amount'],
        method=form.cleaned_data['payment_method'],
        transaction_id=new_transaction_id,
    )

    if new_payment.method == 'pay_4csonline':
        from billing.pay_4csonline.views import start_payment
        return start_payment(request, new_payment.transaction_id)

    raise ValueError('invalid payment method')
