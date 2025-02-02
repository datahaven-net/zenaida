import datetime
import logging

from django.utils import timezone

from accounts.models.account import Account

from billing import orders
from billing import payments


logger = logging.getLogger(__name__)


def identify_domains_for_auto_renew():
    """
    Loop all user accounts and all domains and identify all "almost expired" domains.
    If domain has `auto_renew_enabled=False` will skip it.
    If domain's owner profile has `automatic_renewal_enabled=False` will also skip auto-renew.
    Also will check all existing "domain renew" orders for that user and skip domains that already
    has started orders to renew.
    Returns dictionary with identified users and domains that suppose to be auto renewed.
    """
    domains_to_renew = {}
    for user in Account.users.all():
        if not hasattr(user, 'profile'):
            continue
        expiring_domains = {}
        for domain in user.domains.all():
            if not domain.can_be_renewed:
                # only take in account domains which are registered and active
                continue
            if not domain.auto_renew_enabled:
                continue
            time_domain = domain.expiry_date
            time_now = timezone.now()
            time_delta = time_domain - time_now
            if time_delta.days > 90:
                # domain is not expiring at the moment
                continue
            expiring_domains[domain.name] = domain.expiry_date.date()
        if not expiring_domains:
            continue
        # check if we already created some orders for expiring domains
        existing_renew_order_items = orders.list_order_items(
            owner=user,
            order_item_type='domain_renew',
            order_statuses=['started', 'processing', 'incomplete', ],
        )
        started_domain_renew_items = [itm.name for itm in existing_renew_order_items]
        for domain_name in expiring_domains.keys():
            if domain_name not in started_domain_renew_items:
                if user not in domains_to_renew:
                    domains_to_renew[user] = []
                domains_to_renew[user].append(domain_name)
    return domains_to_renew


def create_auto_renew_orders(domains_to_renew):
    """
    Will create required orders to automatically renew expiring domains for given customers.
    If user has enough balance domain will be automatically renewed - otherwise only order will be created.
    Also email notification will be send to the user unless it is disabled in Profile settings.
    """
    # TODO: ...


def remove_unfinished_orders(status, older_than_days=2):
    unfinished_orders = orders.get_all_orders_by_status_and_older_than_days(
        status=status, older_than_days=older_than_days
    )
    for order in unfinished_orders:
        logger.info(f'Removing {order} because it was not finished after "{older_than_days}" days')
        order.delete()


def retry_failed_orders(max_retries=1):
    failed_orders = orders.list_orders_with_failed_items()
    for order in failed_orders:
        if order.total_price > order.owner.balance:
            logger.info('Not possible to retry failed %r because user %r do not have enough balance', order, order.owner)
            continue
        if order.retries < max_retries:
            logger.info('Going to retry failed %r after %r retries', order, order.retries)
            order.retries = order.retries + 1
            order.save()
            orders.execute_order(order)


def remove_unfinished_payments(past_days=60):
    moment_2months_ago = timezone.now() - datetime.timedelta(days=past_days)
    for payment in payments.iterate_payments(
        started_at__lte=moment_2months_ago,
    ):
        if payment.status == 'processed':
            continue
        payment.delete()
        logger.info(f'Removed {payment} because it was started "{past_days}" days ago and was not processed')
