import ast
import calendar
import logging
import datetime
import os

import pdfkit
from django import shortcuts
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.core import exceptions
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import get_template

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

    is_order_filtered = False
    order_id_list = []
    period = "all"
    if request.method == 'POST':
        form = billing_forms.FilterOrdersByDateForm(request.POST)
        year = form.data.get('year')
        month = form.data.get('month')
        order_objects = billing_orders.list_orders_by_date(
            owner=request.user, year=year, month=month, exclude_cancelled=True
        )
        for order in order_objects:
            order_id_list.append(order.id)
        if not month:
            period = f'{year}'
        else:
            period = f'{year} {calendar.month_name[int(month)]}'
        is_order_filtered = True
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
            'objects': order_objects, 'order_id_list': order_id_list, 'period': period,
            'form': form, 'is_order_filtered': is_order_filtered
        },
    )


def billing_invoice(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')

    if isinstance(ast.literal_eval(request.GET['order_id']), list):
        order_id_list = ast.literal_eval(request.GET['order_id'])
    else:
        order_id_list = [request.GET['order_id']]

    order_objects = []
    for order_id in order_id_list:
        order_objects.append(billing_orders.list_only_processed_orders(owner=request.user, order_id=order_id))

    domain_orders = []
    total_price = 0
    for order in order_objects:
        for order_item in order.items.all():
            domain_orders.append(
                {
                    'domain_name': order_item.name,
                    'transaction_date': order.finished_at.strftime('%d %B %Y'),
                    'price': int(order_item.price)
                }
            )
            total_price += int(order_item.price)

    invoice_period = request.GET.get('period')
    attachment_file_name = f'attachment; filename={invoice_period}_invoice.pdf'
    if not invoice_period:
        # if invoice_period was not given, there is only one order.
        # because of this, invoice period is the month and year of the transaction
        transaction_date = domain_orders[0]['transaction_date']
        invoice_period = transaction_date.split(' ', 1)[1]
        attachment_file_name = f'attachment; filename={transaction_date}_invoice.pdf'

    user_profile = request.user.profile
    html_template = get_template('billing/billing_invoice.html')

    # Fill html template with the domain orders and user profile info
    rendered_html = html_template.render(
        {
            'domain_orders': domain_orders,
            'user_profile': user_profile,
            'total_price': total_price,
            'invoice_period': invoice_period
        }
    )
    # Create pdf file from a html file
    pdfkit.from_string(rendered_html, 'out.pdf')

    with open("out.pdf", "rb") as pdf:
        response = HttpResponse(pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = attachment_file_name
    os.remove("out.pdf")
    return response


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
        raise ValueError()
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
    messages.success(request, 'Order processed successfully.')
    return orders_list(request)


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
    return orders_list(request)


def orders_modify(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')

    order_objects = billing_orders.list_orders(owner=request.user)
    name = request.POST.get('name')

    return shortcuts.render(request, 'billing/account_orders.html', {
        'objects': order_objects,
    }, )


def domain_get_auth_code(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
