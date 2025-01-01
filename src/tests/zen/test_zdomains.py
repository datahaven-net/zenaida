import pytest
import datetime

from django.test import TestCase

from back.models.domain import Domain
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


@pytest.mark.django_db
def test_list_domains():
    tester_domain1 = testsupport.prepare_tester_domain(domain_name='abc.ai', expiry_date=datetime.datetime(2020, 1, 1))
    tester_domain2 = testsupport.prepare_tester_domain(domain_name='xyz.ai', expiry_date=datetime.datetime(2020, 2, 1))
    tester_domain3 = testsupport.prepare_tester_domain(domain_name='www.ai', expiry_date=datetime.datetime(2020, 3, 1))
    assert zdomains.list_domains('tester@zenaida.ai')[0].id == tester_domain1.id
    assert zdomains.list_domains('tester@zenaida.ai')[1].id == tester_domain2.id
    assert zdomains.list_domains('tester@zenaida.ai')[2].id == tester_domain3.id


@pytest.mark.django_db
def test_list_domains_by_status():
    testsupport.prepare_tester_domain(domain_name='abc.ai', expiry_date=datetime.datetime(2020, 1, 1))
    testsupport.prepare_tester_domain(domain_name='xyz.ai', expiry_date=datetime.datetime(2020, 2, 1))
    testsupport.prepare_tester_domain(
        domain_name='www.ai', expiry_date=datetime.datetime(2020, 3, 1), domain_status='to_be_deleted'
    )
    domains = zdomains.list_domains_by_status(status='to_be_deleted')
    assert len(domains) == 1
    assert domains[0].name == 'www.ai'


@pytest.mark.django_db
def test_remove_inactive_domains():
    time_now = datetime.datetime.now()
    testsupport.prepare_tester_domain(domain_name='abc.ai', create_date=(time_now-datetime.timedelta(hours=23)))
    testsupport.prepare_tester_domain(domain_name='xyz.ai', create_date=(time_now-datetime.timedelta(days=2)))

    assert len(Domain.domains.all()) == 2

    zdomains.remove_inactive_domains(days=1)
    assert len(Domain.domains.all()) == 1


@pytest.mark.django_db
def test_remove_inactive_domains_without_create_date():
    domain_1 = testsupport.prepare_tester_domain(domain_name='abc.ai')
    domain_2 = testsupport.prepare_tester_domain(domain_name='xyz.ai')

    domain_1.create_date = None
    domain_1.save()

    assert len(Domain.domains.all()) == 2

    zdomains.remove_inactive_domains(days=1)
    domains = Domain.domains.all()
    assert len(domains) == 1
    assert domains[0].name == 'xyz.ai'


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

    def _prepare_response(self, reg_id=None, admin_id=None, bil_id=None, tech_id=None):
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
            self._prepare_response(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == []
        assert change_registrant is None

    @pytest.mark.django_db
    def test_change_registrant(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_1', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_response(reg_id='registrant_2', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == []
        assert change_registrant == 'registrant_1'

    @pytest.mark.django_db
    def test_add_1_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_response(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id=None)
        )
        assert add_contacts == [{'id': 'tech_0', 'type': 'tech'}, ]
        assert remove_contacts == []
        assert change_registrant is None

    @pytest.mark.django_db
    def test_remove_1_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id=None, bil_id='billing_0', tech_id='tech_0'),
            self._prepare_response(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == [{'id': 'admin_0', 'type': 'admin'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_add_2_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_response(reg_id='registrant_0', admin_id='admin_0', bil_id=None, tech_id=None)
        )
        assert add_contacts == [{'id': 'billing_0', 'type': 'billing'}, {'id': 'tech_0', 'type': 'tech'}, ]
        assert remove_contacts == []
        assert change_registrant is None

    @pytest.mark.django_db
    def test_remove_2_contacts(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id=None, bil_id='billing_0', tech_id=None),
            self._prepare_response(reg_id='registrant_0', admin_id='admin_0', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == []
        assert remove_contacts == [{'id': 'admin_0', 'type': 'admin'}, {'id': 'tech_0', 'type': 'tech'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_switch_1_contact(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_1', bil_id='billing_0', tech_id='tech_0'),
            self._prepare_response(reg_id='registrant_0', admin_id='admin_2', bil_id='billing_0', tech_id='tech_0')
        )
        assert add_contacts == [{'id': 'admin_1', 'type': 'admin'}, ]
        assert remove_contacts == [{'id': 'admin_2', 'type': 'admin'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_switch_2_contacts(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_1', bil_id='billing_1', tech_id='tech_0'),
            self._prepare_response(reg_id='registrant_0', admin_id='admin_2', bil_id='billing_2', tech_id='tech_0')
        )
        assert add_contacts == [{'id': 'admin_1', 'type': 'admin'}, {'id': 'billing_1', 'type': 'billing'}, ]
        assert remove_contacts == [{'id': 'admin_2', 'type': 'admin'}, {'id': 'billing_2', 'type': 'billing'}, ]
        assert change_registrant is None

    @pytest.mark.django_db
    def test_switch_3_contacts(self):
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            self._prepare_domain(reg_id='registrant_0', admin_id='admin_1', bil_id='billing_1', tech_id='tech_1'),
            self._prepare_response(reg_id='registrant_0', admin_id='admin_2', bil_id='billing_2', tech_id='tech_2')
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


class TestDomainUpdateStatuses(TestCase):

    def _prepare_response(self, epp_statuses=None, epp_id=None):
        infData = {'contact': []}
        if epp_statuses:
            infData['status'] = epp_statuses
        if epp_id:
            infData['roid'] = epp_id
        return {'epp': {'response': {'resData': {'infData': infData}}}}

    def test_domain_was_not_updated(self):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abc.ai',
            domain_epp_id='epp123',
            domain_status='to_be_restored',
            domain_epp_statuses={'pendingRestore': 'requested by admin', },
        )
        assert tester_domain.status == 'to_be_restored'
        assert zdomains.domain_update_statuses(tester_domain, domain_info_response=self._prepare_response(
            epp_statuses={'@s': 'pendingRestore', '#text': 'requested by admin', },
            epp_id='epp123',
        ), save=True) is False
        assert tester_domain.epp_id == 'epp123'
        assert tester_domain.epp_statuses['pendingRestore'] == 'requested by admin'
        assert tester_domain.status == 'to_be_restored'

    def test_domain_updated_with_single_status(self):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abc.ai',
            domain_epp_id='epp123',
            domain_status='to_be_restored',
            domain_epp_statuses={'pendingRestore': 'requested by admin', },
        )
        assert tester_domain.status == 'to_be_restored'
        assert zdomains.domain_update_statuses(tester_domain, domain_info_response=self._prepare_response(
            epp_statuses={'@s': 'ok', '#text': 'Active', },
            epp_id='another_epp_id_456',
        ), save=True) is True
        assert tester_domain.epp_id == 'another_epp_id_456'
        assert tester_domain.epp_statuses['ok'] == 'Active'
        assert tester_domain.status == 'active'

    def test_domain_updated_with_multiple_statuses(self):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abc.ai',
            domain_epp_id='epp123',
            domain_status='active',
            domain_epp_statuses={'ok': 'Active', },
        )
        assert tester_domain.status == 'active'
        assert zdomains.domain_update_statuses(tester_domain, domain_info_response=self._prepare_response(
            epp_statuses=[
                {'@s': 'clientUpdateProhibited', '#text': 'Set by admin through UI on Aug 15, 2020 7:21 AM', },
                {'@s': 'clientTransferProhibited', '#text': 'Set by admin through UI on Aug 15, 2020 7:21 AM', },
            ],
            epp_id='another_epp_id_456',
        ), save=True) is True
        assert tester_domain.epp_id == 'another_epp_id_456'
        assert tester_domain.epp_statuses['clientUpdateProhibited'] == 'Set by admin through UI on Aug 15, 2020 7:21 AM'
        assert tester_domain.epp_statuses['clientTransferProhibited'] == 'Set by admin through UI on Aug 15, 2020 7:21 AM'
        assert tester_domain.status == 'active'
