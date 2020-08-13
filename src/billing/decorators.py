from django.contrib import messages

from billing import orders as billing_orders


def create_or_update_single_order(item_type, item_price):
    def decorator(func):
        def wrapper(self, **kwargs):
            domain_name = kwargs.get('domain_name')
            order = None
            started_orders = billing_orders.list_orders(
                owner=self.request.user,
                exclude_cancelled=True,
                include_statuses=['started']
            )
            if started_orders:
                order = started_orders[0]
                kwargs['has_existing_order'] = True
                messages.warning(self.request, 'There is an order you did not complete yet. '
                                               'Please confirm or cancel this order to create a new one')
            if not order:
                order = billing_orders.order_single_item(
                    owner=self.request.user,
                    item_type=item_type,
                    item_price=item_price,
                    item_name=domain_name,
                )
            kwargs['order'] = order
            return func(self, **kwargs)
        return wrapper
    return decorator
