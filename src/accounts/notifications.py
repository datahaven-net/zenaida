import time
import logging

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from django.template.loader import render_to_string

from django.utils.html import strip_tags
from django.utils import timezone

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


def process_notifications_queue(iterations=None, delay=3, iteration_delay=30):
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
        logger.info('finished iteration %d at %r', iteration, timezone.now().isoformat())
        time.sleep(iteration_delay)
