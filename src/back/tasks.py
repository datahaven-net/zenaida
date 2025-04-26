import logging
import datetime

from django.conf import settings
from django.utils import timezone

from back.models.domain import Domain
from back.models.back_end_renew import BackEndRenew

from accounts import notifications

from billing import orders as billing_orders

from epp import rpc_client
from epp import rpc_error

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


def complete_back_end_auto_renewals(critical_days_before_delete=15, dry_run=False):
    moment_now = timezone.now()
    report = []
    accepted_renewals = []
    rejected_renewals = []
    domains_to_be_deleted = []
    renewals = BackEndRenew.renewals.filter(status__in=['started', ])
    for renewal in renewals:
        if not renewal.owner:
            logger.critical('back-end renew notification has no identified owner: %r', renewal)
            continue
        if not renewal.domain:
            logger.critical('back-end renew notification was not attached to a domain: %r', renewal)
            continue
        if renewal.renew_order:
            logger.critical('notification %r was already linked with %r', renewal, renewal.renew_order)
            continue
        renew_years = None
        if renewal.previous_expiry_date:
            if renewal.next_expiry_date:
                renew_years = int(round((renewal.next_expiry_date - renewal.previous_expiry_date).days / 365.0))
            else:
                renew_years = int(round((renewal.domain.expiry_date - renewal.previous_expiry_date).days / 365.0))
        if not renew_years:
            logger.critical('renew duration was not identified for %r', renewal)
            continue
        logger.info('detected %r back-end auto renewal for %r years', renewal.domain, renew_years)
        if renewal.owner.profile.automatic_renewal_enabled and renewal.domain.auto_renew_enabled:
            accepted_renewals.append(renewal)
        else:
            rejected_renewals.append(renewal)

    for renewal in rejected_renewals:
        days_before_expire = (renewal.previous_expiry_date - timezone.now()).days
        if days_before_expire > 0 and days_before_expire < critical_days_before_delete:
            logger.info('domain was about to expire in %d days, but back-end auto renewal %r was rejected by customer', days_before_expire, renewal)
            domains_to_be_deleted.append(renewal)
            continue

    for renewal in accepted_renewals:
        if renewal.owner.balance < settings.ZENAIDA_DOMAIN_PRICE:
            logger.warn('account %r have insufficient balance to complete auto-renew order for %r', renewal.owner, renewal.domain)
            days_before_expire = (renewal.previous_expiry_date - timezone.now()).days
            if days_before_expire > 0 and days_before_expire < critical_days_before_delete:
                logger.info('domain was about to expire in %d days, back-end auto renewal %r will be rejected because of insufficient account balance', days_before_expire, renewal)
                if renewal not in domains_to_be_deleted:
                    domains_to_be_deleted.append(renewal)
                continue
            if days_before_expire <= 0:
                logger.info('domain already expired, back-end auto renewal %r will be rejected because of insufficient account balance', renewal)
                if renewal not in domains_to_be_deleted:
                    domains_to_be_deleted.append(renewal)
                continue
            if renewal.insufficient_balance_email_sent:
                continue
            if dry_run:
                report.append(('insufficient_balance_email_sent', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))
                continue
            notifications.start_email_notification_low_balance_back_end_renew(
                user=renewal.owner,
                domains_list=[renewal.domain.name, ],
            )
            renewal.insufficient_balance_email_sent = True
            renewal.save()
            report.append(('insufficient_balance_email_sent', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))
            continue

        logger.info('domain %r was automatically renew on back-end, creating order retroactively', renewal.domain)
        if dry_run:
            report.append(('processed', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))
            continue
        renewal_order = billing_orders.order_single_item(
            owner=renewal.owner,
            item_type='domain_renew',
            item_price=settings.ZENAIDA_DOMAIN_PRICE,
            item_name=renewal.domain.name,
            item_details={
                'created_automatically': moment_now.isoformat(),
            },
        )
        new_status = billing_orders.execute_order(renewal_order, already_processed=True)
        renewal.renew_order = renewal_order
        if new_status != 'processed':
            renewal.save()
            report.append((new_status, renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, Exception('renew order status is %s' % new_status, ), ))
            logger.critical('for account %r back-end auto renew order status is %r', renewal.owner, new_status)
            continue
        renewal.status = 'processed'
        renewal.save()
        notifications.start_email_notification_domain_renewed(
            user=renewal.owner,
            domain_name=renewal.domain.name,
            expiry_date=renewal.next_expiry_date,
            old_expiry_date=renewal.previous_expiry_date,
        )
        report.append(('processed', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))

    for renewal in domains_to_be_deleted:
        if dry_run:
            report.append(('rejected', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))
            continue
        if 'clientDeleteProhibited' in (renewal.domain.epp_statuses or {}):
            try:
                rpc_client.cmd_domain_update(
                    domain=renewal.domain.name,
                    remove_statuses_list=[{'name': 'clientDeleteProhibited', }],
                )
            except rpc_error.EPPError as exc:
                logger.exception('domain %s failed to remove clientDeleteProhibited status: %r' % (renewal.domain, exc, ))
                report.append(('delete_failed', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))
                continue
        try:
            rpc_client.cmd_domain_delete(renewal.domain.name)
        except rpc_error.EPPError as exc:
            logger.exception('domain %s delete request failed: %r' % (renewal.domain, exc, ))
            report.append(('delete_failed', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))
            continue
        renewal.status = 'rejected'
        renewal.save()
        notifications.start_email_notification_domain_deleted(
            user=renewal.owner,
            domain_name=renewal.domain.name,
        )
        report.append(('rejected', renewal.domain.name, renewal.owner.email, renewal.previous_expiry_date, ))

    return report
