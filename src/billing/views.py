import random
import datetime
import string

from django import shortcuts
from django.conf import settings
from django.utils import timezone
from django.contrib import messages

from billing import forms
from billing.models.payment import Payment


def generate_transaction_id(size=16, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def new_payment(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')

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

    if not settings.BILLING_BYPASS_PAYMENT_TIME_CHECK:
        my_latest_payment = Payment.payments.filter(owner=request.user).latest('started_at')
        if timezone.now() - my_latest_payment.started_at < datetime.timedelta(minutes=3):
            messages.add_message(request, messages.INFO, 'Please wait few minutes and then try again.')
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
        started_at=timezone.now(),
    )

    if new_payment.method == 'pay_4csonline':
        from billing.pay_4csonline.views import start_payment
        return start_payment(request, transaction_id=new_payment.transaction_id)

    raise ValueError('invalid payment method')


def orders_list(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')


def order_create(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')


def order_execute(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    

def domain_get_auth_code(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
