import logging
import os
import calendar

import pdfkit  # @UnresolvedImport

from django import shortcuts
from django.utils import timezone
from django.core import exceptions
from django.template.loader import get_template

from billing.models.order import Order
from billing.models.order_item import OrderItem

from zen import zdomains
from zen import zmaster


def by_id(order_id):
    """
    """
    return Order.orders.filter(id=order_id).first()


def get_order_by_id_and_owner(order_id, owner, log_action=None):
    order = by_id(order_id)
    if not order:
        logging.critical(f'User {owner} tried to {log_action} non-existing order')
        raise exceptions.SuspiciousOperation()
    if order.owner != owner:
        logging.critical(f'User {owner} tried to {log_action} an order for another user')
        raise exceptions.SuspiciousOperation()
    return order


def list_orders(owner, exclude_cancelled=False):
    """
    """
    qs = Order.orders.filter(owner=owner)
    if exclude_cancelled:
        qs = qs.exclude(status='cancelled')
    return list(qs.all())


def list_processed_orders(owner, order_id_list):
    return shortcuts.get_list_or_404(Order.orders.filter(owner=owner, id__in=order_id_list, status='processed'))


def list_orders_by_date(owner, year, month=None, exclude_cancelled=False):
    if year and month:
        orders = Order.orders.filter(owner=owner, started_at__year=year, started_at__month=month)
    elif year:
        orders = Order.orders.filter(owner=owner, started_at__year=year)
    else:
        orders = Order.orders.filter(owner=owner)
    if exclude_cancelled:
        orders = orders.exclude(status='cancelled')
    orders = orders.order_by('finished_at')
    return list(orders.all())


def list_processed_orders_by_date(owner, year, month=None):
    if year and month:
        orders = Order.orders.filter(owner=owner, started_at__year=year, started_at__month=month, status='processed').order_by('finished_at')
    elif year:
        orders = Order.orders.filter(owner=owner, started_at__year=year, status='processed').order_by('finished_at')
    else:
        orders = Order.orders.filter(owner=owner, status='processed').order_by('finished_at')
    return list(orders.all())


def order_single_item(owner, item_type, item_price, item_name):
    """
    """
    new_order = Order.orders.create(
        owner=owner,
        status='started',
        started_at=timezone.now(),
        description='{} {}'.format(item_name, item_type.replace('_', ' ').split(' ')[1]),
    )
    OrderItem.order_items.create(
        order=new_order,
        type=item_type,
        price=item_price,
        name=item_name,
    )
    return new_order


def order_multiple_items(owner, order_items):
    """
    """
    items_by_type = {}
    if len(order_items) == 1:
        description = '{}'.format(order_items[0]['item_type'].replace('_', ' '))
    else:
        description = []
        for order_item in order_items:
            if order_item['item_type'] not in items_by_type:
                items_by_type[order_item['item_type']] = []
            items_by_type[order_item['item_type']].append(order_item)
        for item_type, items_of_that_type in items_by_type.items():
            item_label, _, order_type = item_type.partition('_')
            if len(items_of_that_type) > 1:
                item_label = item_label.replace('domain', 'domains')
            description.append('{} {} {}'.format(order_type, len(items_of_that_type), item_label, ))
        description = ', '.join(description)
    new_order = Order.orders.create(
        owner=owner,
        status='started',
        started_at=timezone.now(),
        description=description,
    )
    for order_item in order_items:
        OrderItem.order_items.create(
            order=new_order,
            type=order_item['item_type'],
            price=order_item['item_price'],
            name=order_item['item_name'],
        )
    return new_order


def update_order_item(order_item, new_status=None, charge_user=False, save=True):
    if charge_user:
        order_item.order.owner.balance -= order_item.price
        if save:
            order_item.order.owner.save()
        order_item.order.finished_at = timezone.now()
        if save:
            order_item.order.save() 
        logging.debug('Charged user %s for "%s"' % (order_item.order.owner, order_item.price))
    if new_status:
        old_status = order_item.status
        order_item.status = new_status
        if save:
            order_item.save()
        logging.debug('Updated status of %s from "%s" to "%s"' % (order_item, old_status, new_status))
        return True
    return False


def execute_domain_register(order_item, target_domain):
    if not zmaster.domain_check_create_update_renew(
        domain_object=target_domain,
        sync_contacts=False,
        sync_nameservers=True,
        renew_years=2,
        log_events=True,
        log_transitions=True,
        raise_errors=False,
    ):
        update_order_item(order_item, new_status='failed', charge_user=False, save=True)
        return False

    update_order_item(order_item, new_status='processed', charge_user=True, save=True)
    return True


def execute_domain_renew(order_item, target_domain):
    if not zmaster.domain_check_create_update_renew(
        domain_object=target_domain,
        sync_contacts=False,
        sync_nameservers=True,
        renew_years=2,
        log_events=True,
        log_transitions=True,
        raise_errors=False,
    ):
        update_order_item(order_item, new_status='failed', charge_user=False, save=True)
        return False

    update_order_item(order_item, new_status='processed', charge_user=True, save=True)
    return True


def execute_domain_restore(order_item, target_domain):
    if not zmaster.domain_restore(
        domain_object=target_domain,
        res_reason='Customer %s requested to restore %s domain' % (order_item.order.owner.email, target_domain.name, ),
        log_events=True,
        log_transitions=True,
        raise_errors=False,
    ):
        update_order_item(order_item, new_status='failed', charge_user=False, save=True)
        return False

    update_order_item(order_item, new_status='processed', charge_user=True, save=True)
    return True


def execute_one_item(order_item):
    target_domain = zdomains.domain_find(order_item.name)
    if not target_domain:
        logging.critical('Domain not exist', order_item.name)
        update_order_item(order_item, new_status='failed', charge_user=False, save=True)
        return False
    if target_domain.owner != order_item.order.owner:
        logging.critical('User %s tried to execute an order with domain from another owner' % order_item.order.owner)
        raise exceptions.SuspiciousOperation()

    if order_item.type == 'domain_register':
        return execute_domain_register(order_item, target_domain)

    if order_item.type == 'domain_renew':
        return execute_domain_renew(order_item, target_domain)

    if order_item.type == 'domain_restore':
        return execute_domain_restore(order_item, target_domain)

    logging.critical('Order item %s have a wrong type' % order_item)
    return False


def execute_single_order(order_object):
    new_status = 'processed'
    total_processed = 0
    # TODO: check/verify every item against Back-end before start processing
    for order_item in order_object.items.all():
        if order_item.status == 'processed':
            continue
        if execute_one_item(order_item):
            total_processed += 1
            continue
        if total_processed > 0:
            new_status = 'incomplete'
            break
        new_status = 'failed'
        break
    old_status = order_object.status
    order_object.status = new_status
    order_object.save()
    logging.debug('Updated status for %s from "%s" to "%s"' % (order_object, old_status, new_status))
    return True if new_status == 'processed' else False


def cancel_single_order(order_object):
    new_status = 'cancelled'
    old_status = order_object.status
    order_object.status = new_status
    order_object.save()
    logging.debug('Updated status for %s from "%s" to "%s"' % (order_object, old_status, new_status))
    return True


def build_receipt(owner, year=None, month=None, order_id=None):
    """
    """
    order_objects = []
    receipt_period = ''
    if order_id:
        order_object = by_id(order_id)
        if not order_object:
            return None
        order_objects.append(order_object)
        receipt_period = order_object.finished_at.strftime('%B %Y')
    else:
        order_objects = list_processed_orders_by_date(owner=owner, year=year, month=month)
        if not order_objects:
            return None
        if year and month:
            month_label = calendar.month_name[int(month)]
            receipt_period = f'{year} {month_label}'
        elif year:
            receipt_period = f'{year}'
        else:
            receipt_period = order_objects[-1].finished_at.strftime('%B %Y')

    domain_orders = []
    total_price = 0
    for order in order_objects:
        for order_item in order.items.all():
            domain_orders.append({
                'domain_name': order_item.name,
                'transaction_date': order.finished_at.strftime('%d %B %Y'),
                'transaction_type': order_item.get_type_display().replace('Domain ', ''),
                'price': int(order_item.price)
            })
            total_price += int(order_item.price)

    # Fill html template with the domain orders and user profile info
    html_template = get_template('billing/billing_receipt.html')
    rendered_html = html_template.render({
        'domain_orders': domain_orders,
        'user_profile': owner.profile,
        'total_price': total_price,
        'receipt_period': receipt_period
    })

    # Create pdf file from a html file
    pdfkit.from_string(rendered_html, 'out.pdf')
    with open("out.pdf", "rb") as pdf_file:
        pdf_raw = pdf_file.read()
    os.remove("out.pdf")
    return {
        'body': pdf_raw,
        'filename': '{}_receipt.pdf'.format(receipt_period.replace(' ', '_')),
    }
