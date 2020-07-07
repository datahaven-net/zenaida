import pytest

from django.test import TestCase

from zen import zdomains

from tests import testsupport


def test_domain_is_valid():
    assert zdomains.is_valid('test.com') is True


def test_domain_is_not_valid():
    assert zdomains.is_valid('-not-valid-domain-.com') is False
    assert zdomains.is_valid('test..ai') is False


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


class TestDomainStatuses(TestCase):
    
    @pytest.mark.django_db
    def test_domain_inactive(self):
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id=None, domain_status='inactive')
        assert tester_domain.is_registered is False
        assert tester_domain.is_blocked is False 
        assert tester_domain.is_suspended is False
        assert tester_domain.can_be_restored is False
        assert tester_domain.can_be_renewed is False
    
    @pytest.mark.django_db
    def test_domain_active(self):
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='active')
        assert tester_domain.is_registered is True
        assert tester_domain.is_blocked is False 
        assert tester_domain.is_suspended is False
        assert tester_domain.can_be_restored is False
        assert tester_domain.can_be_renewed is True
    
    @pytest.mark.django_db
    def test_domain_blocked(self):
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='blocked')
        assert tester_domain.is_registered is True
        assert tester_domain.is_blocked is True
        assert tester_domain.is_suspended is False
        assert tester_domain.can_be_restored is False
        assert tester_domain.can_be_renewed is False
    
    @pytest.mark.django_db
    def test_domain_suspended(self):
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='suspended')
        assert tester_domain.is_registered is True
        assert tester_domain.is_blocked is False
        assert tester_domain.is_suspended is True
        assert tester_domain.can_be_restored is False
        assert tester_domain.can_be_renewed is True
    
    @pytest.mark.django_db
    def test_domain_to_be_deleted(self):
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='to_be_deleted')
        assert tester_domain.is_registered is True
        assert tester_domain.is_blocked is False
        assert tester_domain.is_suspended is False
        assert tester_domain.can_be_restored is True
        assert tester_domain.can_be_renewed is False
    
    @pytest.mark.django_db
    def test_domain_to_be_restored(self):
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', domain_epp_id='epp123', domain_status='to_be_restored')
        assert tester_domain.is_registered is True
        assert tester_domain.is_blocked is False
        assert tester_domain.is_suspended is False
        assert tester_domain.can_be_restored is False
        assert tester_domain.can_be_renewed is False


class TestDomainCompareContacts(TestCase):

    def _prepare_domain(self, reg_id=None, admin_id=None, bil_id=None, tech_id=None):
        epp_id_dict = {}
        if reg_id:
            epp_id_dict['registrant'] = reg_id
        if admin_id:
            epp_id_dict['admin'] = admin_id
        if bil_id:
            epp_id_dict['billing'] = bil_id
        if tech_id:
            epp_id_dict['tech'] = tech_id
        return testsupport.prepare_tester_domain(domain_name='abc.ai', epp_id_dict=epp_id_dict)

    def _prepare_rspnse(self, reg_id=None, admin_id=None, bil_id=None, tech_id=None):
        infData = {'contact': []}
        if reg_id:
            infData['registrant'] = reg_id
        if admin_id:
            infData['contact'].append({'@type': 'admin', '#text': admin_id, })
        if bil_id:
            infData['contact'].append({'@type': 'billing', '#text': bil_id, })
        if tech_id:
            infData['contact'].append({'@type': 'tech', '#text': tech_id, })
        return {'epp': {'response': {'resData': {'infData': infData}}}}

    @pytest.mark.django_db
    def test_no_changes(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == []
        assert change_registrant is None

    @pytest.mark.django_db
    def test_change_registrant(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_1', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_rspnse(reg_id='registrant_2', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == []
        assert change_registrant == 'registrant_1'

    @pytest.mark.django_db
    def test_add_1_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id=None)
        )
        assert add_contacts == [{'id': 'tech_0', 'type': 'tech'}, ]
        assert remove_contacts == []
        assert change_registrant is None

    @pytest.mark.django_db
    def test_remove_1_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id=None, bil_id='billing_0', tech_id='tech_0'),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == [{'id': 'admin_0', 'type': 'admin'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_add_2_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_0', bil_id=None, tech_id=None)
        )
        assert add_contacts == [{'id': 'billing_0', 'type': 'billing'}, {'id': 'tech_0', 'type': 'tech'}, ]
        assert remove_contacts == []
        assert change_registrant is None

    @pytest.mark.django_db
    def test_remove_2_contacts(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id=None, bil_id='billing_0', tech_id=None),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == [{'id': 'admin_0', 'type': 'admin'}, {'id': 'tech_0', 'type': 'tech'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_switch_1_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_1', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_2', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == [{'id': 'admin_1', 'type': 'admin'}, ]
        assert remove_contacts == [{'id': 'admin_2', 'type': 'admin'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_switch_2_contacts(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_1', bil_id='billing_1', tech_id='tech_0'),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_2', bil_id='billing_2', tech_id='tech_0')
        )
        assert add_contacts == [{'id': 'admin_1', 'type': 'admin'}, {'id': 'billing_1', 'type': 'billing'}, ]
        assert remove_contacts == [{'id': 'admin_2', 'type': 'admin'}, {'id': 'billing_2', 'type': 'billing'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_switch_3_contacts(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_1', bil_id='billing_1', tech_id='tech_1'),
            self._prepare_rspnse(reg_id='registrant_0', admin_id='admin_2', bil_id='billing_2', tech_id='tech_2')
        )
        assert add_contacts == [{'id': 'admin_1', 'type': 'admin'}, {'id': 'billing_1', 'type': 'billing'}, {'id': 'tech_1', 'type': 'tech'}, ]
        assert remove_contacts == [{'id': 'admin_2', 'type': 'admin'}, {'id': 'billing_2', 'type': 'billing'}, {'id': 'tech_2', 'type': 'tech'}, ]
        assert change_registrant is None


class TestDomainChangeOwner(TestCase):

    def test_change_owner(self):
        tester1 = testsupport.prepare_tester_account(email='tester1@zenaida.ai')
        tester2 = testsupport.prepare_tester_account(email='tester2@zenaida.ai')
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', tester=tester1)
        assert tester_domain.owner == tester1
        assert tester_domain.registrant.owner == tester1
        tester_domain = zdomains.domain_change_owner(domain_object=tester_domain, new_owner=tester2, also_registrants=False, save=True)
        tester_domain.refresh_from_db()
        assert tester_domain.owner == tester2
        assert tester_domain.registrant.owner == tester1

    def test_change_owner_and_registrants(self):
        tester1 = testsupport.prepare_tester_account(email='tester1@zenaida.ai')
        tester2 = testsupport.prepare_tester_account(email='tester2@zenaida.ai')
        tester_domain = testsupport.prepare_tester_domain(domain_name='abc.ai', tester=tester1)
        assert tester_domain.owner == tester1
        assert tester_domain.registrant.owner == tester1
        tester_domain = zdomains.domain_change_owner(domain_object=tester_domain, new_owner=tester2, also_registrants=True, save=True)
        tester_domain.refresh_from_db()
        assert tester_domain.owner == tester2
        assert tester_domain.registrant.owner == tester2

    def test_change_owner_from_registrant_email_to_new_account(self):
        tester1 = testsupport.prepare_tester_account(email='tester1@zenaida.ai')
        tester1_registrant = testsupport.prepare_tester_registrant(tester=tester1, epp_id='reg1234', profile_object=tester1.profile, create_new=True)
        tester1_contact = testsupport.prepare_tester_contact(tester=tester1, epp_id='admin1234', create_new=True)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abc.ai',
            tester=tester1,
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={'admin': 'admin1234', },
            create_new_registrant=False,
        )
        assert tester_domain.owner == tester1
        assert tester_domain.registrant == tester1_registrant
        assert tester_domain.registrant.owner == tester1
        assert tester_domain.get_contact('admin') == tester1_contact
        assert tester_domain.get_contact('billing') is None
        assert tester_domain.get_contact('tech') is None
        zdomains.domain_change_owner_from_registrant_email(domain_object=tester_domain, new_registrant_email='tester2@zenaida.ai', save=True)
        tester_domain.refresh_from_db()
        assert tester_domain.owner != tester1
        assert tester_domain.registrant != tester1_registrant
        assert tester_domain.registrant.owner != tester1
        assert tester_domain.get_contact('admin') != tester1_contact
        assert tester_domain.get_contact('billing') is None
        assert tester_domain.get_contact('tech') is None

    def test_change_owner_from_registrant_email_to_existing_account(self):
        tester1 = testsupport.prepare_tester_account(email='tester1@zenaida.ai')
        tester1_registrant = testsupport.prepare_tester_registrant(tester=tester1, epp_id='reg1234', profile_object=tester1.profile, create_new=True)
        tester1_contact = testsupport.prepare_tester_contact(tester=tester1, epp_id='admin1234', create_new=True)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abc.ai',
            tester=tester1,
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={'admin': 'admin1234', },
            create_new_registrant=False,
        )
        tester2 = testsupport.prepare_tester_account(email='tester2@zenaida.ai')
        tester2_registrant = testsupport.prepare_tester_registrant(tester=tester2, epp_id='reg5678', profile_object=tester2.profile, create_new=True)
        tester2_contact = testsupport.prepare_tester_contact(tester=tester2, epp_id='tech5678', create_new=True)
        assert tester_domain.owner == tester1
        assert tester_domain.registrant == tester1_registrant
        assert tester_domain.registrant.owner == tester1
        assert tester_domain.get_contact('admin') == tester1_contact
        assert tester_domain.get_contact('billing') is None
        assert tester_domain.get_contact('tech') is None
        zdomains.domain_change_owner_from_registrant_email(domain_object=tester_domain, new_registrant_email='tester2@zenaida.ai', save=True)
        tester_domain.refresh_from_db()
        # tester2_registrant.refresh_from_db
        assert tester_domain.owner == tester2
        assert tester_domain.registrant == tester2_registrant
        assert tester_domain.registrant.owner == tester2
        assert tester_domain.get_contact('admin') == tester2_contact
        assert tester_domain.get_contact('billing') is None
        assert tester_domain.get_contact('tech') is None
