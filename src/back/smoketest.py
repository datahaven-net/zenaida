import logging
import os
import subprocess

from django.conf import settings

from base.push_notifications import PushNotificationService
from base.sms import SMSSender
from base.email import send_email

logger = logging.getLogger(__name__)


def prepare_report(history_filename, history_size=20):
    """
    Reads last few lines from the file and prepare detailed report like that:

           domain1.com        -+++-
             host2.net        +++++
           server3.org        ++-++
 
    """
    proc = subprocess.Popen(['tail', '-n', str(history_size), history_filename], stdout=subprocess.PIPE)
    lines = proc.stdout.readlines()
    last20lines = [l.decode('utf-8').strip() for l in lines]
    report = {host: '' for host in settings.SMOKETEST_HOSTS}
    for line in last20lines:
        for i in range(len(line)):
            report[settings.SMOKETEST_HOSTS[i]] += line[i]
    txt = ''
    for host, checks in report.items():
        txt += '{}   {}\n'.format(host.rjust(20), checks)
    return txt


def single_smoke_test(host):
    """
    Executes system `ping` util to check availability of given host.
    """
    ret_code = os.system(f'ping -c 1 {host} 1>/dev/null')
    return ret_code == 0


def run(history_filename=None, email_alert=False, push_notification_alert=False, sms_alert=False):
    """
    Runs sequence of smoke tests for given hosts from `settings.SMOKETEST_HOSTS` list and fire
    alerts if needed.
    """
    results = ['-', ] * len(settings.SMOKETEST_HOSTS)
    not_healthy = []
    for i in range(len(settings.SMOKETEST_HOSTS)):
        host = settings.SMOKETEST_HOSTS[i]
        if not single_smoke_test(host):
            not_healthy.append(host)
        else:
            results[i] = '+'
    one_line_report = ''.join(results)

    if history_filename:
        with open(history_filename, 'at') as fout:
            fout.write(one_line_report + '\n')

    alerts = []
    if '-' in results:
        if history_filename:
            hosts_txt_report = prepare_report(history_filename)
        else:
            hosts_txt_report = one_line_report + '\n'

        if email_alert:
            for email_address in settings.ALERT_EMAIL_RECIPIENTS:
                alerts.append(('email', email_address, hosts_txt_report, ))
                try:
                    send_email(
                        subject='ZENAIDA ALERT: %s' % (', '.join(not_healthy)),
                        text_content=hosts_txt_report,
                        from_email=settings.EMAIL_ADMIN,
                        to_email=email_address,
                    )
                except:
                    logger.exception('alert EMAIL sending failed')

        if sms_alert:
            alerts.append(('sms', '', hosts_txt_report, ))
            try:
                SMSSender(
                    text_message='ZENAIDA ALERT: %s' % (', '.join(not_healthy))
                ).send_sms()
            except:
                logger.exception('alert SMS sending failed')

        if push_notification_alert:
            alerts.append(('push', '', hosts_txt_report, ))
            try:
                PushNotificationService(
                    notification_message='ZENAIDA ALERT: %s' % (', '.join(not_healthy))
                ).push()
            except:
                logger.exception('alert PUSH notification sending failed')

    return alerts
