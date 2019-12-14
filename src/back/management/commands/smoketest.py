import time
import logging
import requests
import subprocess

from django.core.management.base import BaseCommand
from django.conf import settings

from base.sms import SMSSender
from base.email import send_email

logger = logging.getLogger(__name__)


DOMAINS = [
    'zenaida.cate.ai',
    'offshore.ai',
    'auction.whois.ai',
    'epp.whois.ai',
    'node.bitcoin.ai',
]


def prepare_report(history_filename):
    """
    Reads last 20 lines from the file and prepare detailed report like that:

         zenaida.cate.ai   -+++-
             offshore.ai   +++++
        auction.whois.ai   +++++
            epp.whois.ai   +++++
         node.bitcoin.ai   +++++

    """
    proc = subprocess.Popen(['tail', '-n', '20', history_filename], stdout=subprocess.PIPE)
    lines = proc.stdout.readlines()
    last20lines = [l.decode('utf-8').strip() for l in lines]
    report = {domain: '' for domain in DOMAINS}
    for line in last20lines:
        for i in range(len(line)):
            report[DOMAINS[i]] += line[i]
    txt = ''
    for domain, checks in report.items():
        txt += '{}   {}\n'.format(domain.rjust(20), checks)
    return txt


class Command(BaseCommand):

    help = 'Smoke test script to be executed every 10 minutes'

    def add_arguments(self, parser):
        parser.add_argument('--email_alert', action='store_true', dest='email_alert', default=True)
        parser.add_argument('--sms_alert', action='store_true', dest='sms_alert', default=False)
        parser.add_argument('--history_filename', dest='history_filename', default='/tmp/smoketests')

    def handle(self, email_alert, sms_alert, history_filename, *args, **options):
        results = ['-', ] * len(DOMAINS)
        not_healthy = []
        for i in range(len(DOMAINS)):
            domain = DOMAINS[i]
            try:
                req = requests.get('http://' + domain, verify=False)
                req.raise_for_status()
            except:
                logger.exception('domain %r not healthy' % domain)
                not_healthy.append(domain)
                continue
            results[i] = '+'

        with open(history_filename, 'at') as fout:
            fout.write((''.join(results)) + '\n')

        if '-' in results:
            domains_txt_report = prepare_report(history_filename)

            if email_alert:
                for email_address in settings.ALERT_EMAIL_RECIPIENTS:
                    try:
                        send_email(
                            subject='ZENAIDA ALERT: %s' % (', '.join(not_healthy)),
                            text_content=domains_txt_report,
                            from_email=settings.EMAIL_ADMIN,
                            to_email=email_address,
                        )
                    except:
                        logger.exception('alert email send failed')

            if sms_alert:
                try:
                    SMSSender(
                        text_message='ZENAIDA ALERT: %s' % (', '.join(not_healthy))
                    ).send_sms()
                except:
                    logger.exception('alert sms send failed')
