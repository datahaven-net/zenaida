import pytest

from django.test import TestCase

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


class TestClearContactsChange(TestCase):

    def test_add3_remove3_no_change(self):
        assert zcontacts.clear_contacts_change(
            to_be_added=[
                {'type': 'admin', 'id': 'admin0', },
                {'type': 'billing', 'id': 'billing0', },
                {'type': 'tech', 'id': 'tech0', },
            ],
            to_be_removed=[
                {'type': 'admin', 'id': 'admin0', },
                {'type': 'billing', 'id': 'billing0', },
                {'type': 'tech', 'id': 'tech0', },
            ],
        ) == ([], [], )

    def test_add3_remove3_change1(self):
        assert zcontacts.clear_contacts_change(
            to_be_added=[
                {'type': 'admin', 'id': 'admin1', },
                {'type': 'billing', 'id': 'billing0', },
                {'type': 'tech', 'id': 'tech0', },
            ],
            to_be_removed=[
                {'type': 'admin', 'id': 'admin0', },
                {'type': 'billing', 'id': 'billing0', },
                {'type': 'tech', 'id': 'tech0', },
            ],
        ) == ([{'type': 'admin', 'id': 'admin1', }, ], [{'type': 'admin', 'id': 'admin0', }, ], )

    def test_add3_remove3_change2(self):
        assert zcontacts.clear_contacts_change(
            to_be_added=[
                {'type': 'admin', 'id': 'admin2', },
                {'type': 'billing', 'id': 'billing0', },
                {'type': 'tech', 'id': 'tech2', },
            ],
            to_be_removed=[
                {'type': 'admin', 'id': 'admin0', },
                {'type': 'billing', 'id': 'billing0', },
                {'type': 'tech', 'id': 'tech0', },
            ],
        ) == ([{'type': 'admin', 'id': 'admin2', },
               {'type': 'tech', 'id': 'tech2', }, ],
              [{'type': 'admin', 'id': 'admin0', },
               {'type': 'tech', 'id': 'tech0', }, ], )

    def test_add3_remove0_change3(self):
        assert zcontacts.clear_contacts_change(
            to_be_added=[
                {'type': 'admin', 'id': 'admin0', },
                {'type': 'billing', 'id': 'billing0', },
                {'type': 'tech', 'id': 'tech0', },
            ],
            to_be_removed=[],
        ) == ([{'type': 'admin', 'id': 'admin0', },
               {'type': 'billing', 'id': 'billing0', },
               {'type': 'tech', 'id': 'tech0', }, ], [], )

    def test_add1_remove2_change1(self):
        assert zcontacts.clear_contacts_change(
            to_be_added=[
                {'type': 'admin', 'id': 'admin0', },
            ],
            to_be_removed=[
                {'type': 'admin', 'id': 'admin0', },
                {'type': 'billing', 'id': 'billing0', },
            ],
        ) == ([], [{'type': 'billing', 'id': 'billing0', }, ], )


class TestDomainContactsMerge(TestCase):

    def _make_domain_contacts(self, add_contacts, epp_id_dict, person_names):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abc.ai', domain_epp_id=None,
            add_contacts=add_contacts,
            epp_id_dict=epp_id_dict,
        )
        if 'registrant' in person_names:
            tester_domain.registrant.person_name = person_names['registrant']
            tester_domain.registrant.save()
        if 'admin' in person_names:
            tester_domain.contact_admin.person_name = person_names['admin']
            tester_domain.contact_admin.save()
        if 'billing' in person_names:
            tester_domain.contact_billing.person_name = person_names['billing']
            tester_domain.contact_billing.save()
        if 'tech' in person_names:
            tester_domain.contact_tech.person_name = person_names['tech']
            tester_domain.contact_tech.save()
        return dict(tester_domain.list_contacts(include_registrant=True))

    @pytest.mark.django_db
    def test_skip_registrant(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={'admin': 'id1', 'registrant': 'id2', },
            person_names={'admin': 'Alice', 'registrant': 'Alice', },
        )
        assert domain_contacts['registrant'].epp_id == 'id2'
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'] is None
        assert domain_contacts['tech'] is None
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['registrant'].epp_id == 'id2'
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'] is None
        assert merged_contacts['tech'] is None

    @pytest.mark.django_db
    def test_1_to_1(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={'admin': 'id1', },
            person_names={'admin': 'Alice', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'] is None
        assert domain_contacts['tech'] is None
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'] is None
        assert merged_contacts['tech'] is None

    @pytest.mark.django_db
    def test_2_to_1(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'billing', ],
            epp_id_dict={'admin': 'id1', 'billing': 'id2', },
            person_names={'admin': 'Alice', 'billing': 'Alice', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'].epp_id == 'id2'
        assert domain_contacts['tech'] is None
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id2'
        assert merged_contacts['billing'].epp_id == 'id2'
        assert merged_contacts['tech'] is None

    @pytest.mark.django_db
    def test_2_to_2(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'tech', ],
            epp_id_dict={'admin': 'id1', 'tech': 'id3', },
            person_names={'admin': 'Alice', 'tech': 'Carl', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'] is None
        assert domain_contacts['tech'].epp_id == 'id3'
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'] is None
        assert merged_contacts['tech'].epp_id == 'id3'

    @pytest.mark.django_db
    def test_2_to_2_with_1_unique(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'tech', ],
            epp_id_dict={'admin': 'id1', 'tech': 'id1', },
            person_names={'admin': 'Alice', 'tech': 'Alice', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'] is None
        assert domain_contacts['tech'].epp_id == 'id1'
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'] is None
        assert merged_contacts['tech'].epp_id == 'id1'

    @pytest.mark.django_db
    def test_3_to_1(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'billing', 'tech', ],
            epp_id_dict={'admin': 'id1', 'billing': 'id2', 'tech': 'id3', },
            person_names={'admin': 'Alice', 'billing': 'Alice', 'tech': 'Alice', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'].epp_id == 'id2'
        assert domain_contacts['tech'].epp_id == 'id3'
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id3'
        assert merged_contacts['billing'].epp_id == 'id3'
        assert merged_contacts['tech'].epp_id == 'id3'

    @pytest.mark.django_db
    def test_3_to_2(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'billing', 'tech', ],
            epp_id_dict={'admin': 'id1', 'billing': 'id2', 'tech': 'id3', },
            person_names={'admin': 'Alice', 'billing': 'Bob', 'tech': 'Bob', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'].epp_id == 'id2'
        assert domain_contacts['tech'].epp_id == 'id3'
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'].epp_id == 'id3'
        assert merged_contacts['tech'].epp_id == 'id3'

    @pytest.mark.django_db
    def test_3_to_3(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'billing', 'tech', ],
            epp_id_dict={'admin': 'id1', 'billing': 'id2', 'tech': 'id3', },
            person_names={'admin': 'Alice', 'billing': 'Bob', 'tech': 'Carl', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'].epp_id == 'id2'
        assert domain_contacts['tech'].epp_id == 'id3'
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'].epp_id == 'id2'
        assert merged_contacts['tech'].epp_id == 'id3'

    @pytest.mark.django_db
    def test_3_to_3_with_1_unique(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'billing', 'tech', ],
            epp_id_dict={'admin': 'id1', 'billing': 'id1', 'tech': 'id1', },
            person_names={'admin': 'Alice', 'billing': 'Alice', 'tech': 'Alice', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'].epp_id == 'id1'
        assert domain_contacts['tech'].epp_id == 'id1'
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'].epp_id == 'id1'
        assert merged_contacts['tech'].epp_id == 'id1'

    @pytest.mark.django_db
    def test_3_to_3_with_2_unique(self):
        domain_contacts = self._make_domain_contacts(
            add_contacts=['registrant', 'admin', 'billing', 'tech', ],
            epp_id_dict={'admin': 'id1', 'billing': 'id2', 'tech': 'id2', },
            person_names={'admin': 'Alice', 'billing': 'Bob', 'tech': 'Bob', },
        )
        assert domain_contacts['admin'].epp_id == 'id1'
        assert domain_contacts['billing'].epp_id == 'id2'
        assert domain_contacts['tech'].epp_id == 'id2'
        merged_contacts = zcontacts.merge_contacts(domain_contacts)
        assert merged_contacts['admin'].epp_id == 'id1'
        assert merged_contacts['billing'].epp_id == 'id2'
        assert merged_contacts['tech'].epp_id == 'id2'


@pytest.mark.django_db
def test_get_oldest_registrant():
    tester = testsupport.prepare_tester_account()
    assert zcontacts.get_oldest_registrant(tester) is None
    first_registrant = testsupport.prepare_tester_registrant(tester, epp_id='id1', create_new=True)
    assert zcontacts.registrant_exists(epp_id='id1') is True
    assert zcontacts.registrant_exists(epp_id='id2') is False
    assert zcontacts.registrant_find(epp_id='id1') == first_registrant
    assert zcontacts.get_oldest_registrant(tester) == first_registrant
    second_registrant = testsupport.prepare_tester_registrant(tester, epp_id='id2', create_new=True)
    assert zcontacts.registrant_exists(epp_id='id2') is True
    assert zcontacts.registrant_find(epp_id='id2') != first_registrant
    assert zcontacts.registrant_find(epp_id='id2') == second_registrant
    assert zcontacts.get_oldest_registrant(tester) == first_registrant
    zcontacts.registrant_delete(epp_id='id1')
    assert zcontacts.get_oldest_registrant(tester) == second_registrant
