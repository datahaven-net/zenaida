import time
import json

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError

from django.template.loader import render_to_string

from django.utils.html import strip_tags

from accounts.models.account import Account


class Command(BaseCommand):
    """
    Usage:

        ./venv/bin/python src/manage.py email_announcement --from=admin@zenaida.cate.ai --select=all --template=email/maintenance.html --data={"subject": "system maintenance down-time"}
        ./venv/bin/python src/manage.py email_announcement --select=/tmp/emails_list.txt --template=email/migration.html --data={"subject": "Migration", "date": "20.05.2020"}

    """

    help = 'Sending a email to multiple customers'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--from', dest='from_email', default=None)
        parser.add_argument('-s', '--select', dest='select', default=None)
        parser.add_argument('-t', '--template', dest='template', default=None)
        parser.add_argument('-d', '--data', dest='data', default=None)
        parser.add_argument('-i', '--interval', dest='interval', default=0.2)

    def handle(self, from_email, select, template, data, interval, *args, **options):
        if select is None:
            raise CommandError('Must select target customers: --select=all or --select=/tmp/emails_list.txt')
        if template is None:
            raise CommandError('Must provide a template file path: --template=email/migration.html')
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        selected_users = []
        if select == 'all':
            for user in Account.users.filter(
                is_active=True,
                profile__email_notifications_enabled=True,
            ).exclude(
                is_staff=True,
            ):
                selected_users.append({
                    'email': user.email,
                    'person_name': user.profile.person_name,
                })
        else:
            for user_email in open(select, 'r').read().strip().split('\n'):
                selected_users.append({
                    'email': user_email,
                })
        for to_user in selected_users:
            context = json.loads(data)
            to_email = to_user['email']
            context['email'] = to_email
            context['person_name'] = to_user.get('person_name', 'dear Customer')
            try:
                html_content = render_to_string(template, context=context, request=None)
            except Exception as e:
                raise CommandError('Failed rendering message body: %r' % e)
            text_content = strip_tags(html_content)
            msg = EmailMultiAlternatives(
                subject=context.get('subject', 'Subject'),
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
            time.sleep(interval)
