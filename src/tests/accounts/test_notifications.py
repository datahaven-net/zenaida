import mock
import pytest

from tests import testsupport

from accounts import notifications


@pytest.mark.django_db
def test_start_email_notification_domain_expiring():
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2050-01-01',
    )
    assert new_notification.account == tester
    assert new_notification.recipient == 'tester@zenaida.ai'
    assert new_notification.status == 'started'
    assert new_notification.type == 'email'
    assert new_notification.subject == 'domain_expiring'
    assert new_notification.domain_name == 'abcd.ai'
    assert new_notification.details == {'expiry_date': '2050-01-01', }


@pytest.mark.django_db
def test_start_email_notification_domain_renewed():
    tester = testsupport.prepare_tester_account(account_balance=123.45)
    new_notification = notifications.start_email_notification_domain_renewed(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2050-01-01',
        old_expiry_date='2048-01-01',
    )
    assert new_notification.account == tester
    assert new_notification.recipient == 'tester@zenaida.ai'
    assert new_notification.status == 'started'
    assert new_notification.type == 'email'
    assert new_notification.subject == 'domain_renewed'
    assert new_notification.domain_name == 'abcd.ai'
    assert new_notification.details == {
        'expiry_date': '2050-01-01',
        'old_expiry_date': '2048-01-01',
        'current_balance': 123.45,
    }


@pytest.mark.django_db
def test_start_email_notification_low_balance():
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_low_balance(
        user=tester,
        expiring_domains_list=['abcd.ai', ],
    )
    assert new_notification.account == tester
    assert new_notification.recipient == 'tester@zenaida.ai'
    assert new_notification.status == 'started'
    assert new_notification.type == 'email'
    assert new_notification.subject == 'low_balance'
    assert new_notification.domain_name == ''
    assert new_notification.details == {'expiring_domains_list': ['abcd.ai', ], }


@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_execute_email_notification_success(mock_send):
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2050-01-01',
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
        expiry_date='2050-01-01',
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
        expiry_date='2050-01-01',
    )
    mock_send.return_value = True
    notifications.process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
    new_notification.refresh_from_db()
    assert new_notification.status == 'sent'


@pytest.mark.django_db
@mock.patch('accounts.notifications.EmailMultiAlternatives.send')
def test_process_notifications_queue_with_failed(mock_send):
    tester = testsupport.prepare_tester_account()
    new_notification = notifications.start_email_notification_domain_expiring(
        user=tester,
        domain_name='abcd.ai',
        expiry_date='2050-01-01',
    )
    mock_send.side_effect = Exception('some error while sending')
    notifications.process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
    new_notification.refresh_from_db()
    assert new_notification.status == 'failed'
