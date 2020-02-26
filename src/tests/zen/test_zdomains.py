import pytest

from zen import zdomains

from tests import testsupport


def test_domain_is_valid():
    assert zdomains.is_valid('test.com') is True

def test_domain_is_not_valid():
    assert zdomains.is_valid('-not-valid-domain-.com') is False

@pytest.mark.django_db
def test_domain_find():
    tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai')
    assert zdomains.domain_find(domain_name='abc.ai').id == tester_domain.id

@pytest.mark.django_db
def test_domain_find_not_registered():
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='abc.ai',
        domain_epp_id=None,
        create_date=None,
        expiry_date=None,
    )
    assert zdomains.domain_find(domain_name='abc.ai').id == tester_domain.id

@pytest.mark.django_db
def test_domain_inactive():
    tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id=None, domain_status='inactive')
    assert tester_domain.is_registered is False
    assert tester_domain.is_blocked is False 
    assert tester_domain.is_suspended is False
    assert tester_domain.can_be_restored is False
    assert tester_domain.can_be_renewed is False

@pytest.mark.django_db
def test_domain_active():
    tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='active')
    assert tester_domain.is_registered is True
    assert tester_domain.is_blocked is False 
    assert tester_domain.is_suspended is False
    assert tester_domain.can_be_restored is False
    assert tester_domain.can_be_renewed is True

@pytest.mark.django_db
def test_domain_blocked():
    tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='blocked')
    assert tester_domain.is_registered is True
    assert tester_domain.is_blocked is True
    assert tester_domain.is_suspended is False
    assert tester_domain.can_be_restored is False
    assert tester_domain.can_be_renewed is False

@pytest.mark.django_db
def test_domain_suspended():
    tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='suspended')
    assert tester_domain.is_registered is True
    assert tester_domain.is_blocked is False
    assert tester_domain.is_suspended is True
    assert tester_domain.can_be_restored is False
    assert tester_domain.can_be_renewed is True

@pytest.mark.django_db
def test_domain_to_be_deleted():
    tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='to_be_deleted')
    assert tester_domain.is_registered is True
    assert tester_domain.is_blocked is False
    assert tester_domain.is_suspended is False
    assert tester_domain.can_be_restored is True
    assert tester_domain.can_be_renewed is False

@pytest.mark.django_db
def test_domain_to_be_restored():
    tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='to_be_restored')
    assert tester_domain.is_registered is True
    assert tester_domain.is_blocked is False
    assert tester_domain.is_suspended is False
    assert tester_domain.can_be_restored is False
    assert tester_domain.can_be_renewed is False
