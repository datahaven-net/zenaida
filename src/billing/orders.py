import logging

from django.utils import timezone

from billing.models.order import Order
from billing.models.order_item import OrderItem

from automats import domain_synchronizer


def by_id(order_id):
    """
    """
    try:
        return Order.orders.get(id=order_id)
    except:
        return None


def list_orders(owner):
    """
    """
    return list(Order.orders.filter(owner=owner).all())


def order_single_item(owner, item_type, item_price, item_name):
    """
    """
    new_order = Order.orders.create(
        owner=owner,
        status='started',
        started_at=timezone.now(),
        description='{} {}'.format(item_name, item_type.replace('_', ' ')),
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


def execute_single_order(order_object):
    new_status = 'processed'
    total_processed = 0
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


def update_order_item(order_item, new_status=None, save=True):
    if new_status:
        old_status = order_item.status
        order_item.status = new_status
        order_item.save()
        logging.debug('Updated status of %s from "%s" to "%s"' % (order_item, old_status, new_status))
        return True
    return False


def execute_one_item(order_item):
    if order_item.type == 'domain_register':
        ds = domain_synchronizer.DomainSynchronizer(
            log_events=True,
            log_transitions=True,
            raise_errors=True,
        )
        ds.event('run', order_item.name, renew_years=2, sync_contacts=True, sync_nameservers=True)
        outputs = list(ds.outputs)
        del ds
        if not outputs[-1]:
            update_order_item(order_item, new_status='failed', save=True)
            return False
        update_order_item(order_item, new_status='processed', save=True)
        return True

    if order_item.type == 'domain_renew':
        ds = domain_synchronizer.DomainSynchronizer(
            log_events=True,
            log_transitions=True,
            raise_errors=True,
        )
        ds.event('run', order_item.name, renew_years=2, sync_contacts=True, sync_nameservers=True)
        outputs = list(ds.outputs)
        del ds
        if not outputs[-1]:
            update_order_item(order_item, new_status='failed', save=True)
            return False
        update_order_item(order_item, new_status='processed', save=True)
        return True

    if order_item.type == 'domain_restore':
        # TODO: domain_restore to be implemented later
        update_order_item(order_item, new_status='failed', save=True)
        return False

    logging.critical('Order item %s have a wrong type' % order_item)
    return False
