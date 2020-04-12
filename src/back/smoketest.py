import logging
import os
import requests

from django.conf import settings

from base.push_notifications import PushNotificationService
from base.sms import SMSSender
from base.email import send_email

logger = logging.getLogger(__name__)


def prepare_report(history_filename):
    """
    Reads each line from the file and prepare detailed report like that:

           domain1.com        -+++-
             host2.net        +++++
           server3.org        ++-++
 
    """
    report_text = ""
    with open(history_filename, 'r') as health_check_file:
        for index, line in enumerate(health_check_file):
            report_text += f"{settings.SMOKETEST_HOSTS[index]}   {line}"

    return report_text


def single_smoke_test(host, method='ping'):
    """
    Executes system `ping` util to check availability of given host.
    """
    if method in ['http', 'https', ]:
        try:
            req = requests.get('%s://%s' % (method, host, ),  verify=False)
            req.raise_for_status()
        except:
            return False
        return True
    ret_code = os.system(f'ping -c 1 {host} 1>/dev/null')
    return ret_code == 0


def run(history_filename, email_alert=False, push_notification_alert=False, sms_alert=False):
    """
    Runs sequence of smoke tests for given hosts from `settings.SMOKETEST_HOSTS` list and fire
    alerts if needed.
    """

    health_results = ["-", ] * len(settings.SMOKETEST_HOSTS)
    for index, host in enumerate(settings.SMOKETEST_HOSTS):
        method = 'ping'
        if host.startswith('http://'):
            method = 'http'
            host = host.replace('http://', '')
        elif host.startswith('https://'):
            method = 'https'
            host = host.replace('https://', '')
        elif host.startswith('ping://'):
            method = 'ping'
            host = host.replace('ping://', '')
        if single_smoke_test(host, method):
            health_results[index] = "+"

    # If file is empty, write health results for the first time.
    try:
        file_exists_but_empty = os.stat(history_filename).st_size == 0
        file_does_not_exist = False
    except Exception:
        file_does_not_exist = True
        file_exists_but_empty = False

    if file_exists_but_empty or file_does_not_exist:
        with open(history_filename, "w") as health_check_file:
            health_check_file.write("\n".join(health_results))
        return

    unhealthy_hosts = []
    updated_lines_of_file = ""
    with open(history_filename, 'r') as health_check_file:
        for index, line in enumerate(health_check_file):
            # Add health of the host to its line.
            updated_line = line.strip()+f"{health_results[index]}\n"
            # Do not make any line more than 20 characters.
            if len(updated_line) == 20:
                updated_line = updated_line[1:]
            updated_lines_of_file += updated_line
            # If last X amount of health checks are negative, add that host to the unhealthy hosts group.
            if updated_line.split('\n')[0].endswith(settings.SMOKETEST_MAXIMUM_UNAVAILABLE_AMOUNT * '-'):
                unhealthy_hosts.append(settings.SMOKETEST_HOSTS[index])

    # Update the file with the new values.
    with open(history_filename, "w") as health_check_file:
        health_check_file.write(updated_lines_of_file)

    alerts = []
    if unhealthy_hosts:
        hosts_txt_report = prepare_report(history_filename)

        if email_alert:
            for email_address in settings.ALERT_EMAIL_RECIPIENTS:
                alerts.append(('email', email_address, hosts_txt_report, ))
                try:
                    send_email(
                        subject='ZENAIDA ALERT: %s' % (', '.join(unhealthy_hosts)),
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
                    text_message='ZENAIDA ALERT: %s' % (', '.join(unhealthy_hosts))
                ).send_sms()
            except:
                logger.exception('alert SMS sending failed')

        if push_notification_alert:
            alerts.append(('push', '', hosts_txt_report, ))
            try:
                PushNotificationService(
                    notification_message='ZENAIDA ALERT: %s' % (', '.join(unhealthy_hosts))
                ).push()
            except:
                logger.exception('alert PUSH notification sending failed')

    return alerts
