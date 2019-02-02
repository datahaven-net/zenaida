import logging
import datetime

from django import shortcuts
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.core import exceptions
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from back import domains

from billing import forms
from billing import orders
from billing import payments


def billing_overview(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')


def new_payment(request):
    """
    """
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
        my_latest_payment = payments.latest_payment(request.user)
        if my_latest_payment:
            if timezone.now() - my_latest_payment.started_at < datetime.timedelta(minutes=3):
                messages.add_message(request, messages.INFO, 'Please wait few minutes and then try again.')
                return shortcuts.render(request, 'billing/new_payment.html', {
                    'form': form,
                })

    new_payment = payments.start_payment(
        owner=request.user,
        amount=form.cleaned_data['amount'],
        payment_method=form.cleaned_data['payment_method'],
        
    )

    if new_payment.method == 'pay_4csonline':
        from billing.pay_4csonline.views import start_payment
        return start_payment(request, transaction_id=new_payment.transaction_id)

    raise ValueError('invalid payment method')


def orders_list(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    order_objects = orders.list_orders(owner=request.user)
    page = request.GET.get('page', 1)
    paginator = Paginator(order_objects, 10)
    try:
        order_objects = paginator.page(page)
    except PageNotAnInteger:
        order_objects = paginator.page(1)
    except EmptyPage:
        order_objects = paginator.page(paginator.num_pages)
    return shortcuts.render(request, 'billing/account_orders.html', {
        'objects': order_objects,
    }, )


def payments_list(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    payment_objects = payments.list_payments(owner=request.user, statuses=['processed', ])
    page = request.GET.get('page', 1)
    paginator = Paginator(payment_objects, 10)
    try:
        payment_objects = paginator.page(page)
    except PageNotAnInteger:
        payment_objects = paginator.page(1)
    except EmptyPage:
        payment_objects = paginator.page(paginator.num_pages)
    return shortcuts.render(request, 'billing/account_payments.html', {
        'objects': payment_objects,
    }, )


def order_domain_register(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    new_order = orders.order_single_item(
        owner=request.user,
        item_type='domain_register',
        item_price=100.0,
        item_name=request.GET['domain_name'],
    )
    return shortcuts.render(request, 'billing/order.html', {
        'order': new_order,
    }, )


def order_domain_renew(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')


def order_domain_restore(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')


def order_create(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    order_items = request.POST.getlist('order_items')
    to_be_ordered = []
    for domain_name in order_items:
        domain_object = domains.find(domain_name=domain_name)
        if not domain_object:
            raise ValueError()
        if domain_object.owner != request.user:
            logging.critical('User %s tried to make an order with domain from another owner' % request.user)
            raise exceptions.SuspiciousOperation()
        item_type = 'domain_register'
        if domain_object.can_be_restored:
            item_type = 'domain_restore'
        elif domain_object.is_registered:
            item_type = 'domain_renew'
        to_be_ordered.append(dict(
            item_type=item_type,
            item_price=100.0,
            item_name=domain_object.name,
        ))
    if not to_be_ordered:
        raise ValueError()
    new_order = orders.order_multiple_items(
        owner=request.user,
        order_items=to_be_ordered,
    )
    return shortcuts.render(request, 'billing/order.html', {
        'order': new_order,
    }, )


def order_details(request, order_id):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    existing_order = orders.by_id(order_id)
    return shortcuts.render(request, 'billing/order.html', {
        'order': existing_order,
    }, )


def order_execute(request, order_id):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    existing_order = orders.by_id(order_id)
    if not existing_order:
        logging.critical('User %s tried to execute non-existing order' % request.user)
        raise exceptions.SuspiciousOperation()
    if not existing_order.owner == request.user:
        logging.critical('User %s tried to execute an order for another user' % request.user)
        raise exceptions.SuspiciousOperation()
    if not orders.execute_single_order(existing_order):
        messages.add_message(request, messages.ERROR, 'There were technical problems with order processing.'
                                                      'Please try again later or contact customer support.')
    return shortcuts.render(request, 'billing/order.html', {
        'order': existing_order,
    }, )


def orders_modify(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')

    order_objects = orders.list_orders(owner=request.user)
    name = request.POST.get('name')

    return shortcuts.render(request, 'billing/account_orders.html', {
        'objects': order_objects,
    }, )


def domain_get_auth_code(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
