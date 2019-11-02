import mock
import pytest
import datetime

from django.utils import timezone

from tests import testsupport

from accounts import notifications
from accounts.models.notification import Notification


@pytest.mark.django_db
def test_start_email_notification_domain_expiring():
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2020-01-01',
    )
    assert new_notification.account == tester
    assert new_notification.recipient == 'tester@zenaida.ai'
    assert new_notification.status == 'started'
    assert new_notification.type == 'email'
    assert new_notification.subject == 'domain_expiring'
    assert new_notification.domain_name == 'abcd.ai'
    assert new_notification.details == {'expiry_date': '2020-01-01', }
    

@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_execute_email_notification_success(mock_send):
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2020-01-01',
    )
    mock_send.return_value = True
    assert notifications.execute_email_notification(new_notification) is True


@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_execute_email_notification_failed(mock_send):
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2020-01-01',
    )
    mock_send.side_effect = Exception('some error while sending')
    assert notifications.execute_email_notification(new_notification) is False


@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_process_notifications_queue_with_success(mock_send):
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2020-01-01',
    )
    mock_send.return_value = True
    notifications.process_notifications_queue(iterations=1, delay=0.1)
    new_notification.refresh_from_db()
    assert new_notification.status == 'sent'


@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_process_notifications_queue_with_failed(mock_send):
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2020-01-01',
    )
    mock_send.side_effect = Exception('some error while sending')
    notifications.process_notifications_queue(iterations=1, delay=0.1)
    new_notification.refresh_from_db()
    assert new_notification.status == 'failed'


@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_check_notify_domain_expiring_email_sent_and_executed(mock_send):
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    outgoing_emails = notifications.check_notify_domain_expiring(dry_run=False)
    assert len(outgoing_emails) == 1
    assert outgoing_emails[0][0] == tester
    assert outgoing_emails[0][1] == tester_domain.name
    mock_send.return_value = True
    notifications.process_notifications_queue(iterations=1, delay=0.1)
    new_notification = Notification.notifications.first()
    assert new_notification.status == 'sent'


@pytest.mark.django_db
def test_check_notify_domain_expiring_email_sent():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    outgoing_emails = notifications.check_notify_domain_expiring(dry_run=True)
    assert len(outgoing_emails) == 1
    assert outgoing_emails[0][0] == tester
    assert outgoing_emails[0][1] == tester_domain.name


@pytest.mark.django_db
def test_check_notify_domain_expiring_email_not_sent():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=180)  # expiry_date 180 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    outgoing_emails = notifications.check_notify_domain_expiring(dry_run=True)
    assert len(outgoing_emails) == 0


@pytest.mark.django_db
def test_check_notify_domain_expiring_when_alread_expired():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=10)  # already expired 10 days ago
    tester_domain.status = 'active'
    tester_domain.save()
    outgoing_emails = notifications.check_notify_domain_expiring(dry_run=True)
    assert len(outgoing_emails) == 0


@pytest.mark.django_db
def test_check_notify_domain_expiring_when_not_active():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'inactive'
    tester_domain.save()
    outgoing_emails = notifications.check_notify_domain_expiring(dry_run=True)
    assert len(outgoing_emails) == 0


@pytest.mark.django_db
def test_account_profile_email_notifications_disabled():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester.profile.email_notifications_enabled = False
    tester.profile.save()
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    outgoing_emails = notifications.check_notify_domain_expiring(dry_run=False)
    assert len(outgoing_emails) == 0


@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_no_duplicated_emails(mock_send):
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    # first time
    outgoing_emails = notifications.check_notify_domain_expiring(dry_run=False)
    assert len(outgoing_emails) == 1
    assert outgoing_emails[0][0] == tester
    assert outgoing_emails[0][1] == tester_domain.name
    mock_send.return_value = True
    notifications.process_notifications_queue(iterations=1, delay=0.1)
    new_notification = Notification.notifications.first()
    assert new_notification.status == 'sent'
    # second time
    outgoing_emails_again = notifications.check_notify_domain_expiring(dry_run=False)
    assert len(outgoing_emails_again) == 0
    # third time
    outgoing_emails_one_more = notifications.check_notify_domain_expiring(dry_run=False)
    assert len(outgoing_emails_one_more) == 0
