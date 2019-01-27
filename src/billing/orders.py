from django.utils import timezone

from billing.models.order import Order
from billing.models.order_item import OrderItem


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
