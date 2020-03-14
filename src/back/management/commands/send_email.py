from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError

from django.template.loader import render_to_string

from django.utils.html import strip_tags


class Command(BaseCommand):
    """
    Usage:

        ./venv/bin/python src/manage.py send_email --to=recipient@gmail.com

    """

    help = 'Sending testing email based on current Django configuration'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--to', dest='to_email')
        parser.add_argument('-f', '--from', dest='from_email', default=None)
        parser.add_argument('-s', '--subject', dest='subject', default='test email from Zenaida host')

    def handle(self, to_email, from_email, subject, *args, **options):
        if not to_email:
            raise CommandError('Must provide email recipient: --to=person@gmail.com')
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        context = {
            'subject': subject,
        }
        email_template = 'email/test_email.html'
        html_content = render_to_string(email_template, context=context, request=None)
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            subject=context['subject'],
            body=text_content,
            from_email=from_email,
            to=[to_email, ],
            bcc=[to_email, ],
            cc=[to_email, ],
        )
        msg.attach_alternative(html_content, 'text/html')
        if msg.send():
            self.stdout.write(self.style.SUCCESS('message sent to %r' % to_email))
        else:
            self.stdout.write(self.style.ERROR('failed sending message to %r' % to_email))
