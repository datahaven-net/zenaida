import time
import logging

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from django.template.loader import render_to_string

from django.utils.html import strip_tags
from django.utils import timezone

from accounts.models.account import Account
from accounts.models.notification import Notification

logger = logging.getLogger(__name__)


def start_email_notification_domain_expiring(user, domain_name, expiry_date):
    new_notification = Notification.notifications.create(
        account=user,
        recipient=user.profile.contact_email,
        type='email',
        subject='domain_expiring',
        domain_name=domain_name,
        details={
            'expiry_date': expiry_date,
        },
    )
    logger.info('created new %r', new_notification)
    return new_notification


def execute_email_notification(notification_object):
    from_email = settings.DEFAULT_FROM_EMAIL
    email_template = None
    context = {
        'person_name': notification_object.account.profile.person_name or 'dear customer',
        'domain_name': notification_object.domain_name,
    }
    if notification_object.subject == 'domain_expiring':
        email_template = 'email/domain_expiring.html'
        context.update({
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'subject': 'AI domain is expiring',
        })

    html_content = render_to_string(email_template, context=context, request=None)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        context['subject'],
        text_content,
        from_email,
        to=[notification_object.recipient, ],
        bcc=[notification_object.recipient, ],
        cc=[notification_object.recipient, ],
    )
    msg.attach_alternative(html_content, 'text/html')
    try:
        msg.send()
    except:
        return False
    return True


def process_email_notifications_queue(iterations=None, delay=3):
    """
    Looping thru all email notifications and execute those which was was not sent yet.
    """
    iteration = 0
    while True:
        if iterations is not None and iteration >= iterations:
            break
        iteration += 1
        for one_notification in Notification.objects.filter(
            status='started',
            type='email',
        ):
            try:
                result = execute_email_notification(one_notification)
            except:
                result = False
            if result:
                one_notification.status = 'sent'
                one_notification.save()
                logger.info('successfully executed %r', one_notification)
            else:
                one_notification.status = 'failed'
                one_notification.save()
                logger.exception('failed to execute %r' % one_notification)
            time.sleep(delay)


def check_notify_domain_expiring(dry_run=True):
    """
    Loop all user accounts and all domains and identify all "expiring" domains:
    less than 90 days left before domain get expired based on `expiry_date` field.
    If `dry_run` is True only print out identified users and domains.
    Otherwise actually will send email notifications about those domains.
    Also checks notifications history to make sure only one email was sent for given domain.
    Skip sending if user disabled email notifications in Profile settings.
    """
    for user in Account.users.all():
        if not user.profile.email_notifications_enabled:
            continue
        expiring_domains = {}
        for domain in user.domains.all():
            if not domain.epp_id or domain.status != 'active':
                # only take in account domains which are registered and active
                continue
            t_domain = domain.expiry_date
            t_now = timezone.now()
            dt = t_domain - t_now
            if dt.days > 90:
                # domain is not expiring at the moment
                continue
            if dt.days <= 0:
                # domain already expired - no email needed
                continue
            expiring_domains[domain.name] = domain.expiry_date
        domains_to_be_notified = []
        # now look up all already sent notifications and find only domains
        # which we did not send notification yet
        domains_notified = user.notifications.values_list('domain_name', flat=True)
        domains_to_be_notified = list(set(expiring_domains.keys()).difference(set(domains_notified)))
        if not domains_to_be_notified:
            continue
        if dry_run:
            logger.info('for %r following domains are expiring: %r', user, domains_to_be_notified)
            continue
        for expiring_domain in domains_to_be_notified:
            start_email_notification_domain_expiring(
                user=user,
                domain_name=expiring_domain,
                expiry_date=expiring_domains[expiring_domain],
            )
