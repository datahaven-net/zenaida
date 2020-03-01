import pytest
import datetime

from django.utils import timezone

from tests import testsupport

from billing import tasks


@pytest.mark.django_db
def test_identify_domains_for_auto_renew():
    tester = testsupport.prepare_tester_account()
    tester.profile.automatic_renewal_enabled = True
    tester.profile.save()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {tester: ['abcd.ai', ]}


@pytest.mark.django_db
def test_identify_domains_for_auto_renew_automatic_renewal_disabled():
    tester = testsupport.prepare_tester_account()
    tester.profile.automatic_renewal_enabled = False
    tester.profile.save()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {}


@pytest.mark.django_db
def test_identify_domains_for_auto_renew_can_not_be_renewed():
    tester = testsupport.prepare_tester_account()
    tester.profile.automatic_renewal_enabled = True
    tester.profile.save()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_status='inactive',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {}


@pytest.mark.django_db
def test_identify_domains_for_auto_renew_order_already_exist():
    tester = testsupport.prepare_tester_account()
    tester.profile.automatic_renewal_enabled = True
    tester.profile.save()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abcd.ai',
        tester=tester,
        domain_epp_id='aaa123',
    )
    tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
    tester_domain.status = 'active'
    tester_domain.save()
    # TODO: test order exists already
    domains_to_renew = tasks.identify_domains_for_auto_renew()
    assert domains_to_renew == {tester: ['abcd.ai', ]}
