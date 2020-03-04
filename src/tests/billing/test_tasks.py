import pytest
import datetime

from django.utils import timezone

from tests import testsupport

from billing import tasks


@pytest.mark.django_db
def test_identify_domains_for_auto_renew():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
        auto_renew_enabled=True,
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {tester: ['abcd.ai', ]}


@pytest.mark.django_db
def test_identify_domains_for_auto_renew_auto_renew_disabled():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
        auto_renew_enabled=False,
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {}


@pytest.mark.django_db
def test_identify_domains_for_auto_renew_can_not_be_renewed():
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_status='inactive',
        auto_renew_enabled=True,
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {}

