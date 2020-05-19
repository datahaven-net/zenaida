import datetime
import logging

from django.conf import settings
from django.utils import timezone

from accounts.models.account import Account
from accounts.models.activation import Activation
from accounts import notifications

logger = logging.getLogger(__name__)


def activations_cleanup():
    """
    If the activation_code is older than a certain time of period and the account is still inactive (no domain,
    balance or payment belongs to the account as well), removes the inactive account and the expired activation code.

    If the activation_code is older than a certain time of period but the account is still active, then removes
    only the activation code.
    """

    activation_code_expiry_time = timezone.now() - datetime.timedelta(
        minutes=settings.ACTIVATION_CODE_EXPIRING_MINUTE
    )
    expired_activation_code_objects = Activation.objects.filter(
        created_at__lte=activation_code_expiry_time
    )

    for activation_code in expired_activation_code_objects:
        account = activation_code.account
        if not account.is_active:
            if account.balance == 0 and len(account.domains.all()) == 0 and len(account.payments.all()) == 0:
                activation_code.account.delete()  # This will remove activation code as well.
                logger.info("inactive account removed: %r", account.email)
                continue
        activation_code.delete()
        logger.info("activation code removed: %r", activation_code.code)


def check_notify_domain_expiring(dry_run=True, min_days_before_expire=0, max_days_before_expire=30, subject='domain_expiring'):
    """
    Loop all user accounts and all domains and identify all "expiring" domains.

    Skip sending any notifications if user disabled email notifications in Profile settings.
    Also checks notifications history to make sure only one email is sent for given domain.

    Values `min_days_before_expire` and `max_days_before_expire` will select domains based on `expiry_date` field.

    Parameter `subject` must be one of "domain_expiring" or "domain_expire_soon".

    If `dry_run` is True only returns identified users and domains without taking any actions.
    """
    time_now = timezone.now()
    outgoing_emails = []
    for user in Account.users.all():
        if not hasattr(user, 'profile'):
            continue
        if not user.profile.email_notifications_enabled:
            continue
        expiring_domains = {}
        for domain in user.domains.all():
            if not domain.epp_id or domain.status in ['inactive', ]:
                # only take in account domains which are registered and active
                continue
            time_domain = domain.expiry_date
            time_delta = time_domain - time_now
            if time_delta.days >= max_days_before_expire:
                # domain is not expiring at the moment or must be handled in another task
                continue
            if time_delta.days <= min_days_before_expire:
                # domain already expired or must be handled in another task - no email needed
                continue
            expiring_domains[domain.name] = domain.expiry_date.date()
        # now look up all already sent notifications and find only domains
        # which we did not send notification yet
        domains_notified = user.notifications.filter(subject=subject).values_list('domain_name', flat=True)
        domains_to_be_notified = list(set(expiring_domains.keys()).difference(set(domains_notified)))
        # TODO: need to also clean up old notifications
        if not domains_to_be_notified:
            continue
        for expiring_domain in domains_to_be_notified:
            logger.info('for %r domain %r is expiring and has not been communicated yet', user, expiring_domain)
            outgoing_emails.append((user, expiring_domain, expiring_domains[expiring_domain], ))
            if dry_run:
                continue
            notifications.start_email_notification_domain_expiring(
                user=user,
                domain_name=expiring_domain,
                expiry_date=expiring_domains[expiring_domain],
                subject=subject,
            )
    return outgoing_emails
