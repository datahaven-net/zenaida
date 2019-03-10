import pytest

from zen import zcontacts

from tests import testsupport


@pytest.mark.django_db
def test_contact_create():
    tester = testsupport.prepare_tester_account(email='my@zenaida.ai')
    tester_contact = zcontacts.contact_create(
        epp_id='abcd',
        owner=tester,
        person_name='Tester Tester',
        organization_name='TestingCorp',
        address_street='TestStreet',
        address_city='TestCity',
        address_province='TestProvince',
        address_postal_code='TestPostalCode',
        address_country='AI',
        contact_voice='1234567890',
        contact_fax='1234567890',
        contact_email='tester@zenaida.ai',
    )
    assert tester_contact.owner.email == 'my@zenaida.ai'


@pytest.mark.django_db
def test_contact_create_from_profile():
    tester = testsupport.prepare_tester_account(email='my@zenaida.ai')
    tester_contact = zcontacts.contact_create_from_profile(owner=tester, profile_object=tester.profile)
    assert tester_contact.owner.email == 'my@zenaida.ai'
