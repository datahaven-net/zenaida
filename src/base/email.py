import logging

from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_email(subject, text_content, from_email, to_email, html_content=None, ):
    msg = EmailMultiAlternatives(subject, text_content, from_email, to=[to_email, ], bcc=[to_email, ], cc=[to_email, ])
    try:
        msg.send()
    except:
        logger.exception('Failed to send email')
