import logging
import datetime

from django import shortcuts
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.core import exceptions
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from back import domains

from billing import forms as billing_forms
from billing import orders as billing_orders
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
        form = billing_forms.NewPaymentForm()
        return shortcuts.render(request, 'billing/new_payment.html', {
            'form': form,
        })

    form = billing_forms.NewPaymentForm(request.POST)
    if not form.is_valid():
        return shortcuts.render(request, 'billing/new_payment.html', {
            'form': form,
        })

    if not settings.BILLING_BYPASS_PAYMENT_TIME_CHECK:
        my_latest_payment = payments.latest_payment(request.user)
        if my_latest_payment:
            if timezone.now() - my_latest_payment.started_at < datetime.timedelta(minutes=3):
                messages.info(request, 'Please wait few minutes and then try again.')
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
    if request.method == 'POST':
        form = billing_forms.FilterOrdersByDateForm(request.POST)
        order_objects = billing_orders.list_orders_by_date(
            owner=request.user,
            year=form.data.get('year'),
            month=form.data.get('month'),
            exclude_cancelled=True,
        )
    else:
        form = billing_forms.FilterOrdersByDateForm()
        order_objects = billing_orders.list_orders(owner=request.user, exclude_cancelled=True)
    page = request.GET.get('page', 1)
    paginator = Paginator(order_objects, 10)
    try:
        order_objects = paginator.page(page)
    except PageNotAnInteger:
        order_objects = paginator.page(1)
    except EmptyPage:
        order_objects = paginator.page(paginator.num_pages)
    return shortcuts.render(
        request, 'billing/account_orders.html', {
            'objects': order_objects,
            'form': form,
        },
    )


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
    new_order = billing_orders.order_single_item(
        owner=request.user,
        item_type='domain_register',
        item_price=100.0,
        item_name=request.GET['domain_name'],
    )
    return shortcuts.render(request, 'billing/order_details.html', {
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
        messages.error(request, 'No domains were selected.')
        return shortcuts.redirect('billing_orders')
    new_order = billing_orders.order_multiple_items(
        owner=request.user,
        order_items=to_be_ordered,
    )
    return shortcuts.render(request, 'billing/order_details.html', {
        'order': new_order,
    }, )


def order_details(request, order_id):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    existing_order = billing_orders.by_id(order_id)
    return shortcuts.render(request, 'billing/order_details.html', {
        'order': existing_order,
    }, )


def order_execute(request, order_id):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    existing_order = billing_orders.by_id(order_id)
    if not existing_order:
        logging.critical('User %s tried to execute non-existing order' % request.user)
        raise exceptions.SuspiciousOperation()
    if not existing_order.owner == request.user:
        logging.critical('User %s tried to execute an order for another user' % request.user)
        raise exceptions.SuspiciousOperation()
    if not billing_orders.execute_single_order(existing_order):
        messages.error(request, 'There were technical problems with order processing. '
                                                      'Please try again later or contact customer support.')
    else:
        messages.success(request, 'Order processed successfully.')
    return shortcuts.redirect('billing_orders')


def order_cancel(request, order_id):
    """
    """    
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    existing_order = billing_orders.by_id(order_id)
    if not existing_order:
        logging.critical('User %s tried to cancel non-existing order' % request.user)
        raise exceptions.SuspiciousOperation()
    if not existing_order.owner == request.user:
        logging.critical('User %s tried to cancel an order for another user' % request.user)
        raise exceptions.SuspiciousOperation()
    billing_orders.cancel_single_order(existing_order)
    messages.success(request, 'Order of %s cancelled.' % existing_order.description)
    return shortcuts.redirect('billing_orders')


def orders_modify(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')

    order_objects = billing_orders.list_orders(owner=request.user)
    name = request.POST.get('name')

    return shortcuts.render(request, 'billing/account_orders.html', {
        'objects': order_objects,
    }, )


def order_receipt_download(request, order_id=None):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    if order_id:
        pdf_info = billing_orders.build_receipt(
            owner=request.user,
            order_id=order_id,
        )
    else:
        pdf_info = billing_orders.build_receipt(
            owner=request.user,
            year=request.GET.get('year'),
            month=request.GET.get('month'),
        )
    if not pdf_info:
        return shortcuts.redirect('billing_orders')
    response = HttpResponse(pdf_info['body'], content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={pdf_info["filename"]}'
    return response


def domain_get_auth_code(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
