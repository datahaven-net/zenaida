import pytest

from tests import testsupport

from accounts import notifications


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
