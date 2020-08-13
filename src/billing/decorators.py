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
            # Check if there is already an order with a single item for the same domain. If so, update existing order.
            for started_order in started_orders:
                if started_order.items_count == 1:
                    order_item = started_order.items.all()[0]
                    if order_item.name == domain_name:
                        order = billing_orders.update_order_with_order_item(
                            owner=self.request.user,
                            order=order_item.order,
                            order_item=order_item,
                            item_type=item_type,
                            item_price=item_price,
                            item_name=domain_name,
                        )
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
