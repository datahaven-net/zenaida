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
    )
    OrderItem.order_items.create(
        order=new_order,
        type=item_type,
        price=item_price,
        name=item_name,
    )
    return new_order


def order_multiple_items(owner):
    """
    """
    new_order = Order.orders.create(
        owner=owner,
        status='started',
        started_at=timezone.now(),
    )
    OrderItem.order_items.create(
        order=new_order,
        type=item_type,
        price=item_price,
        name=item_name,
    )
    return 
