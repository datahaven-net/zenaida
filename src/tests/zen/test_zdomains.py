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
