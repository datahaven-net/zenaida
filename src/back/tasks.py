import logging
import datetime

from django.conf import settings
from django.utils import timezone

from back.models.domain import Domain

from accounts import notifications

from billing import orders as billing_orders

from zen import zmaster
from zen import zusers

logger = logging.getLogger(__name__)


def sync_expired_domains(dry_run=True):
    """
    When domain is expired COCCA back-end suppose to suspend it and send polling notification to Zenaida.
    But it is also possible that COCCA move it to another registrar - for example to put it on auction.
    In that case notification is not sent for some reason and Zenaida potentially can display wrong information to user.
    To workaround that we can keep track of all domains that are just expired few minutes ago and fetch the actual
    info from COCCA back-end for those. This way Zenaida will recognize the latest status of the domain and take
    required actions: remove domain from Zenaida DB.
    """
    moment_now = timezone.now()
    expired_active_domains = Domain.domains.filter(
        expiry_date__lte=moment_now,
        status__in=['active', 'suspended', ],
    ).exclude(
        epp_id=None,
    )
    report = []
    for expired_domain in expired_active_domains:
        logger.info('domain %r is expired, going to synchronize from back-end', expired_domain)
        if dry_run:
            result = []
        else:
            result = zmaster.domain_synchronize_from_backend(
                domain_name=expired_domain.name,
                create_new_owner_allowed=False,
                domain_transferred_away=True,
                soft_delete=False,
            )
        report.append((expired_domain, result, ))
    return report


def auto_renew_expiring_domains(dry_run=True, min_days_before_expire=60, max_days_before_expire=90):
    """
    When customer enables "domain auto-renew" feature on "My Profile" page and possess enough account balance
    Zenaida must take care of his expiring domains and automatically renew them 3 months before the expiration date.
    The task is checking all expiring domains and for those which has enabled `auto_renew_enabled` flag performs
    such actions:
        1. create a renew order on behalf of customer
        2. execute the order right away if customer possess enough account balance
        3. send a email notification to customer
        4. if user do not have enough account balance, will send a "low_balance" notification
        5. checks notifications history to keep only one "low_balance" email per 30 days
        6. also task will make an attempt to auto-renew already suspended and expired domains
    if `dry_run` is True will only return a list of domains to be automatically renewed.
    """
    report = []
    users_on_low_balance = {}
    moment_now = timezone.now()

    moment_min_days_before_expire = timezone.now() + datetime.timedelta(days=min_days_before_expire)
    moment_max_days_before_expire = timezone.now() + datetime.timedelta(days=max_days_before_expire)
    expiring_active_domains = Domain.domains.filter(
        expiry_date__gte=moment_min_days_before_expire,
        expiry_date__lte=moment_max_days_before_expire,
        status__in=['active', ],
    ).exclude(
        epp_id=None,
    )
    for expiring_domain in expiring_active_domains:
        if not expiring_domain.auto_renew_enabled:
            continue
        if not expiring_domain.owner.profile.automatic_renewal_enabled:
            continue
        if billing_orders.find_pending_domain_renew_order_items(expiring_domain.name):
            logger.warn('domain renew order already started for %r', expiring_domain.name)
            continue
        current_expiry_date = expiring_domain.expiry_date
        if expiring_domain.owner.balance < settings.ZENAIDA_DOMAIN_PRICE:
            # step 4: user is on low balance
            report.append((expiring_domain.name, expiring_domain.owner.email, Exception('not enough funds'), ))
            if expiring_domain.owner.email not in users_on_low_balance:
                users_on_low_balance[expiring_domain.owner.email] = []
            users_on_low_balance[expiring_domain.owner.email].append(expiring_domain.name)
            logger.warn('not enough funds to auto-renew domain %r', expiring_domain.name)
            continue
        if dry_run:
            report.append((expiring_domain.name, expiring_domain.owner.email, current_expiry_date, ))
            continue
        logger.info('domain %r is expiring, going to start auto-renew now', expiring_domain.name)
        # step 1: create domain renew order
        renewal_order = billing_orders.order_single_item(
            owner=expiring_domain.owner,
            item_type='domain_renew',
            item_price=settings.ZENAIDA_DOMAIN_PRICE,
            item_name=expiring_domain.name,
            item_details={
                'created_automatically': moment_now.isoformat(),
            },
        )
        # step 2: execute the order
        new_status = billing_orders.execute_order(renewal_order)
        expiring_domain.refresh_from_db()
        if new_status != 'processed':
            report.append((expiring_domain.name, expiring_domain.owner.email, Exception('renew order status is %s' % new_status, ), ))
            logger.info('for account %r renew order status is %r', expiring_domain.owner, new_status)
            continue
        if not expiring_domain.owner.profile.email_notifications_enabled:
            report.append((expiring_domain.name, expiring_domain.owner.email, Exception('email notifications are disabled', ), ))
            logger.info('skip "domain_renewed" notification, email notifications are disabled for account %r', expiring_domain.owner)
            continue
        # step 3: send a notification to the customer
        notifications.start_email_notification_domain_renewed(
            user=expiring_domain.owner,
            domain_name=expiring_domain.name,
            expiry_date=expiring_domain.expiry_date,
            old_expiry_date=current_expiry_date,
        )
        report.append((expiring_domain.name, expiring_domain.owner.email, expiring_domain.expiry_date, ))

    expired_suspended_domains = Domain.domains.filter(
        expiry_date__lte=moment_now,
        status__in=['suspended', ],
    ).exclude(
        epp_id=None,
    )
    # step 6: make an attempt to auto-renew already suspended and expired domains
    for expired_domain in expired_suspended_domains:
        if not expired_domain.auto_renew_enabled:
            continue
        if not expired_domain.owner.profile.automatic_renewal_enabled:
            continue
        if billing_orders.find_pending_domain_renew_order_items(expired_domain.name):
            logger.warn('domain renew order already started for %r', expired_domain.name)
            continue
        current_expiry_date = expired_domain.expiry_date
        if expired_domain.owner.balance < settings.ZENAIDA_DOMAIN_PRICE:
            # step 4: user is on low balance
            report.append((expired_domain.name, expired_domain.owner.email, Exception('not enough funds'), ))
            if expired_domain.owner.email not in users_on_low_balance:
                users_on_low_balance[expired_domain.owner.email] = []
            users_on_low_balance[expired_domain.owner.email].append(expired_domain.name)
            logger.warn('not enough funds to auto-renew domain %r', expired_domain.name)
            continue
        if dry_run:
            report.append((expired_domain.name, expired_domain.owner.email, current_expiry_date, ))
            continue
        logger.info('domain %r is expired, going to start auto-renew now', expired_domain.name)
        # step 1: create domain renew order
        renewal_order = billing_orders.order_single_item(
            owner=expired_domain.owner,
            item_type='domain_renew',
            item_price=settings.ZENAIDA_DOMAIN_PRICE,
            item_name=expired_domain.name,
            item_details={
                'created_automatically': moment_now.isoformat(),
            },
        )
        # step 2: execute the order
        new_status = billing_orders.execute_order(renewal_order)
        expired_domain.refresh_from_db()
        if new_status != 'processed':
            report.append((expired_domain.name, expired_domain.owner.email, Exception('renew order status is %s' % new_status, ), ))
            logger.info('for account %r renew order status is %r', expired_domain.owner, new_status)
            continue
        if not expired_domain.owner.profile.email_notifications_enabled:
            report.append((expired_domain.name, expired_domain.owner.email, Exception('email notifications are disabled', ), ))
            logger.info('skip "domain_renewed" notification, email notifications are disabled for account %r', expired_domain.owner)
            continue
        # step 3: send a notification to the customer
        notifications.start_email_notification_domain_renewed(
            user=expired_domain.owner,
            domain_name=expired_domain.name,
            expiry_date=expired_domain.expiry_date,
            old_expiry_date=current_expiry_date,
        )
        report.append((expired_domain.name, expired_domain.owner.email, expired_domain.expiry_date, ))

    for one_user_email, user_domain_names in users_on_low_balance.items():
        one_user = zusers.find_account(one_user_email)
        if not one_user.profile.email_notifications_enabled:
            one_domain_name = ''
            if user_domain_names:
                one_domain_name = user_domain_names[0]
            report.append((one_domain_name, one_user.email, Exception('email notifications are disabled', ), ))
            logger.info('skip "low_balance" notification, email notifications are disabled for account %r', one_user)
            continue
        recent_low_balance_notification = one_user.notifications.filter(
            subject='low_balance',
            created_at__gte=(moment_now - datetime.timedelta(days=30)),
        ).first()
        if recent_low_balance_notification:
            # step 5: found recent notification, skip
            report.append((None, one_user.email, Exception('notification already sent recently'), ))
            logger.info('skip "low_balance" notification, notification already sent recently for account %r', one_user)
            continue
        if dry_run:
            report.append((None, one_user.email, True, ))
            continue
        notifications.start_email_notification_low_balance(one_user, expiring_domains_list=user_domain_names)

    return report
