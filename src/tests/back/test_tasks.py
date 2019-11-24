import mock
import pytest
import datetime

from django.utils import timezone

from tests import testsupport

from back import tasks


@pytest.mark.django_db
def test_sync_expired_domains_dry_run():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
    tester_domain.status = 'active'
    tester_domain.save()
    report = tasks.sync_expired_domains(dry_run=True)
    assert len(report) == 1
    assert report[0] == (tester_domain, [], )


@pytest.mark.django_db
@mock.patch('zen.zmaster.domain_synchronize_from_backend')
def test_sync_expired_domains_ok(mock_domain_synchronize_from_backend):
    mock_domain_synchronize_from_backend.return_value = ['ok', ]
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
    tester_domain.status = 'active'
    tester_domain.save()
    report = tasks.sync_expired_domains(dry_run=False)
    assert len(report) == 1
    assert report[0] == (tester_domain, ['ok', ], )


@pytest.mark.django_db
def test_sync_expired_domains_skipped_not_expired():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=1)  # not expired yet
    tester_domain.status = 'active'
    tester_domain.save()
    report = tasks.sync_expired_domains(dry_run=False)
    assert len(report) == 0


@pytest.mark.django_db
def test_sync_expired_domains_skipped_not_active():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
    tester_domain.status = 'inactive'
    tester_domain.save()
    report = tasks.sync_expired_domains(dry_run=False)
    assert len(report) == 0
