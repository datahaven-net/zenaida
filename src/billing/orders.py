import logging

from django import shortcuts
from django.utils import timezone
from django.core import exceptions

from billing.models.order import Order
from billing.models.order_item import OrderItem

from back import domains

from zepp import zmaster


def by_id(order_id):
    """
    """
    try:
        return Order.orders.get(id=order_id)
    except:
        return None


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
    if not month:
        orders = Order.orders.filter(owner=owner, started_at__year=year)
    else:
        orders = Order.orders.filter(owner=owner, started_at__year=year, started_at__month=month)

    if exclude_cancelled:
        orders = orders.exclude(status='cancelled')
    return list(orders.all())


def order_single_item(owner, item_type, item_price, item_name):
    """
    """
    new_order = Order.orders.create(
        owner=owner,
        status='started',
        started_at=timezone.now(),
        description='{}'.format(item_type.replace('_', ' ')),
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
            description.append('{} {}'.format(
                len(items_of_that_type),
                item_type.replace('_', ' ').replace('domain', 'domains')))
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
        sync_nameservers=False,
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


def execute_one_item(order_item):
    target_domain = domains.find(order_item.name)
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
        # TODO: execute_domain_restore() to be implemented later
        update_order_item(order_item, new_status='failed', charge_user=False, save=True)
        return False

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
