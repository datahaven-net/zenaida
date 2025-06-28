import time
import logging

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from django.template.loader import render_to_string

from django.utils.html import strip_tags

from accounts.models.notification import Notification

logger = logging.getLogger(__name__)


def start_email_notification_account_approved(user):
    new_notification = Notification.notifications.create(
        account=user,
        recipient=user.email,
        type='email',
        subject='account_approved',
    )
    logger.info('created new %r', new_notification)
    return new_notification


def start_email_notification_domain_expiring(user, domain_name, expiry_date, subject='domain_expiring'):
    new_notification = Notification.notifications.create(
        account=user,
        recipient=user.profile.contact_email,
        type='email',
        subject=subject,
        domain_name=domain_name,
        details={
            'expiry_date': expiry_date,
        },
    )
    logger.info('created new %r', new_notification)
    return new_notification


def start_email_notification_domain_renewed(user, domain_name, expiry_date, old_expiry_date):
    new_notification = Notification.notifications.create(
        account=user,
        recipient=user.profile.contact_email,
        type='email',
        subject='domain_renewed',
        domain_name=domain_name,
        details={
            'expiry_date': expiry_date,
            'old_expiry_date': old_expiry_date,
            'current_balance': user.balance,
        },
    )
    logger.info('created new %r', new_notification)
    return new_notification


def start_email_notification_domain_deleted(user, domain_name, expiry_date, restore_end_date, delete_end_date, insufficient_balance):
    new_notification = Notification.notifications.create(
        account=user,
        recipient=user.profile.contact_email,
        type='email',
        subject='domain_deleted',
        domain_name=domain_name,
        details={
            'expiry_date': expiry_date,
            'restore_end_date': restore_end_date,
            'delete_end_date': delete_end_date,
            'insufficient_balance': insufficient_balance,
        },
    )
    logger.info('created new %r', new_notification)
    return new_notification


def start_email_notification_low_balance(user, expiring_domains_list=[]):
    new_notification = Notification.notifications.create(
        account=user,
        recipient=user.profile.contact_email,
        type='email',
        subject='low_balance',
        domain_name='',
        details={
            'expiring_domains_list': expiring_domains_list,
        },
    )
    logger.info('created new %r', new_notification)
    return new_notification


def start_email_notification_low_balance_back_end_renew(user, domains_list=[]):
    new_notification = Notification.notifications.create(
        account=user,
        recipient=user.profile.contact_email,
        type='email',
        subject='low_balance_back_end_renew',
        domain_name='',
        details={
            'domains_list': domains_list,
        },
    )
    logger.info('created new %r', new_notification)
    return new_notification


def execute_email_notification(notification_object):
    from_email = settings.DEFAULT_FROM_EMAIL
    email_template = None
    context = {
        'site_name': settings.SITE_NAME,
        'site_url': settings.SITE_BASE_URL,
    }
    if notification_object.subject == 'domain_expiring':
        email_template = 'email/domain_expiring.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'subject': 'AI domain is expiring',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'domain_expire_soon':
        email_template = 'email/domain_expire_soon.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'subject': 'AI domain will expire after 30 days',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'domain_expire_in_5_days':
        email_template = 'email/domain_expire_in_5_days.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'subject': 'AI domain will expire in few days',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'domain_expire_in_3_days':
        email_template = 'email/domain_expire_in_3_days.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'subject': 'AI domain will expire in 3 days',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'domain_expire_in_1_day':
        email_template = 'email/domain_expire_in_1_day.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'subject': 'AI domain will expire in 24 hours',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'low_balance':
        email_template = 'email/low_balance.html'
        context.update({
            'expiring_domains_list': notification_object.details.get('expiring_domains_list', []),
            'subject': 'AI account balance insufficient for auto-renew',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'low_balance_back_end_renew':
        email_template = 'email/low_balance_back_end_renew.html'
        context.update({
            'domains_list': notification_object.details.get('domains_list', []),
            'subject': 'AI account balance insufficient for domain auto-renew',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'domain_renewed':
        email_template = 'email/domain_renewed.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date_prev': notification_object.details.get('old_expiry_date'),
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'duration_years': settings.ZENAIDA_DOMAIN_RENEW_YEARS,
            'current_balance': notification_object.details.get('current_balance'),
            'subject': 'AI domain is automatically renewed',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'domain_deleted':
        email_template = 'email/domain_deleted.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'domain_restore_end_date': notification_object.details.get('restore_end_date'),
            'domain_delete_end_date': notification_object.details.get('delete_end_date'),
            'insufficient_balance': 'insufficient account balance' if notification_object.details.get('insufficient_balance') else 'disabled auto-renewal configuration',
            'subject': 'AI domain expired',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'domain_deactivated':
        email_template = 'email/domain_deactivated.html'
        context.update({
            'domain_name': notification_object.domain_name,
            'domain_expiry_date': notification_object.details.get('expiry_date'),
            'subject': 'AI domain is deactivated',
            'person_name': notification_object.account.profile.person_name or 'dear Customer',
        })
    elif notification_object.subject == 'account_approved':
        email_template = 'email/account_approved.html'
        context.update({
            'subject': '%s account was activated' % settings.SITE_NAME,
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


def process_notifications_queue(iterations=None, delay=3, iteration_delay=5*60):
    """
    Looping thru all email notifications and execute those which was was not sent yet.
    """
    iteration = 0
    while True:
        if iterations is not None and iteration >= iterations:
            break
        iteration += 1
        # TODO: able to handle SMS notifications
        for one_notification in Notification.notifications.filter(
            status='started',
            type='email',
        ):
            if one_notification.subject != 'account_approved':
                if not hasattr(one_notification.account, 'profile'):
                    one_notification.status = 'skipped'
                    one_notification.save()
                    logger.info('skipped (no profile) %r', one_notification)
                    time.sleep(delay)
                    continue
                if not one_notification.account.profile.email_notifications_enabled:
                    one_notification.status = 'skipped'
                    one_notification.save()
                    logger.info('skipped %r', one_notification)
                    time.sleep(delay)
                    continue
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
        time.sleep(iteration_delay)
