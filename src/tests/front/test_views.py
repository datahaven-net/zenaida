# coding=utf-8
import copy
import datetime
import os
import mock
import pytest
import socket

from django.test import TestCase, override_settings
from django.conf import settings

from back.models import contact
from back.models.contact import Contact, Registrant
from back.models.domain import Domain
from back.models.profile import Profile
from back.models.zone import Zone
from billing import orders as billing_orders
from tests.testsupport import (
    prepare_tester_account, prepare_tester_contact, prepare_tester_registrant, prepare_tester_profile,
)
from epp import rpc_error
from zen import zusers


contact_person = {
    'person_name': 'TesterA',
    'organization_name': 'TestingCorporation',
    'address_street': 'Testers Boulevard 123',
    'address_city': 'Testopia',
    'address_province': 'TestingLands',
    'address_postal_code': '1234AB',
    'address_country': 'NL',
    'contact_voice': '+31612341234',
    'contact_fax': '+31656785678',
    'contact_email': 'tester_contact@zenaida.ai',
}


class BaseAuthTesterMixin(object):

    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.account.profile.contact_email = 'tester@zenaida.ai'
        self.account.profile.save()
        registrant_info = copy.deepcopy(contact_person)
        registrant_info['owner'] = self.account
        Registrant.registrants.create(**registrant_info)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestAccountDomainsListView(BaseAuthTesterMixin, TestCase):

    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    def test_domain_list_successful(self, mock_user_profile_complete, mock_list_contacts):
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock()]
        Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
        )
        response = self.client.get('/domains/')
        assert response.status_code == 200
        assert len(response.context['object_list']) == 1

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_profile_is_not_complete(self, mock_user_profile_complete):
        mock_user_profile_complete.return_value = False
        response = self.client.get('/domains/')
        assert response.status_code == 302
        assert response.url == '/profile/'

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_registrant_not_exist(self, mock_user_profile_complete):
        self.account.registrants.first().delete()
        mock_user_profile_complete.return_value = True
        response = self.client.get('/domains/')
        assert response.status_code == 302
        assert response.url == '/profile/'

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_contact_info_is_not_complete(self, mock_user_profile_complete):
        mock_user_profile_complete.return_value = True
        response = self.client.get('/domains/')
        assert response.status_code == 200
        assert len(response.context['object_list']) == 0


class TestIndexViewForLoggedInUser(BaseAuthTesterMixin, TestCase):

    def test_index_page_successful(self):
        with mock.patch('back.models.profile.Profile.is_complete') as mock_user_profile_complete:
            with mock.patch('zen.zcontacts.list_contacts') as mock_list_contacts:
                mock_user_profile_complete.return_value = True
                mock_list_contacts.return_value = [True, ]
                response = self.client.get('')
        assert response.status_code == 200
        assert response.context['total_domains'] == 0

    def test_index_page_redirects_to_profile_page(self):
        response = self.client.get('')
        assert response.status_code == 302
        assert response.url == '/profile/'

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_index_page_not_redirects_to_contacts_page(self, mock_user_profile_complete):
        mock_user_profile_complete.return_value = True
        with mock.patch('zen.zcontacts.list_contacts') as mock_list_contacts:
            mock_list_contacts.return_value = []
        response = self.client.get('')
        assert response.status_code == 200
        assert response.context['total_domains'] == 0


class TestIndexViewForUnknownUser(TestCase):

    def test_index_page_successful(self):
        response = self.client.get('')
        assert response.status_code == 200


class TestAccountDomainCreateView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zzones.is_supported')
    @mock.patch('zen.zmaster.domains_check')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_create_domain_successful(self, mock_domains_check, mock_zone_is_supported, mock_user_profile_complete):
        mock_domains_check.return_value = {'test.ai': False, }
        mock_zone_is_supported.return_value = True
        mock_user_profile_complete.return_value = True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)
            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id,
            ))
            assert response.status_code == 302
            assert response.url == '/billing/order/create/register/test.ai/'
            assert len(Domain.domains.all()) == 1

    @pytest.mark.django_db
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zzones.is_supported')
    @mock.patch('zen.zmaster.domains_check')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_create_domain_successful_without_contacts(self, mock_domains_check, mock_zone_is_supported, mock_user_profile_complete):
        mock_domains_check.return_value = {'test.ai': False, }
        mock_zone_is_supported.return_value = True
        mock_user_profile_complete.return_value = True
        registrant_info = copy.deepcopy(contact_person)
        registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
        Registrant.registrants.create(**registrant_info)
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='ns1.google.com',
        ))
        assert response.status_code == 302
        assert response.url == '/billing/order/create/register/test.ai/'
        assert len(Domain.domains.all()) == 1

    @pytest.mark.django_db
    @mock.patch('zen.zdomains.domain_find')
    @mock.patch('back.models.profile.Profile.is_complete')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_domain_is_already_registered(self, mock_user_profile_complete, mock_domain_find):
        mock_user_profile_complete.return_value = True
        mock_domain_find.return_value = mock.MagicMock(
            epp_id='12345',
        )
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)
            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id,
            ))
            assert response.status_code == 302
            assert response.url == '/domains/'
            assert len(Domain.domains.all()) == 0

    @pytest.mark.django_db
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zzones.is_supported')
    @mock.patch('zen.zmaster.domains_check')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_domain_is_already_registered_on_backend(self, mock_domains_check, mock_zone_is_supported, mock_user_profile_complete):
        mock_domains_check.return_value = {'test.ai': True, }
        mock_zone_is_supported.return_value = True
        mock_user_profile_complete.return_value = True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)
            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id,
            ))
            assert response.status_code == 302
            assert response.url == '/domains/'
            assert len(Domain.domains.all()) == 0

    @pytest.mark.django_db
    @mock.patch('zen.zdomains.domain_find')
    @mock.patch('back.models.profile.Profile.is_complete')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_domain_is_in_another_users_basket(self, mock_user_profile_complete, mock_domain_find):
        """
        Test when domain is someone's basket and if it's hold for an hour. So user can't register that domain.
        """
        mock_user_profile_complete.return_value = True
        mock_domain_find.return_value = mock.MagicMock(
            epp_id=None,
            create_date=datetime.datetime.utcnow(),
        )
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)
            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id,
            ))
            assert response.status_code == 302
            assert response.url == '/domains/'
            assert len(Domain.domains.all()) == 0

    @pytest.mark.django_db
    @mock.patch('zen.zdomains.domain_find')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zzones.is_supported')
    @mock.patch('zen.zmaster.domains_check')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_domain_is_available_after_1_hour(
        self, mock_domains_check, mock_zone_is_supported, mock_user_profile_complete, mock_domain_find
    ):
        """
        Test after domain was someone's basket for an hour, user can still register it.
        """
        mock_domains_check.return_value = {'test.ai': False, }
        mock_zone_is_supported.return_value = True
        mock_user_profile_complete.return_value = True
        mock_domain_find.return_value = mock.MagicMock(
            epp_id=None,
            create_date=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            id=1,
        )
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)
            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id,
            ))
            assert response.status_code == 302
            assert response.url == '/billing/order/create/register/test.ai/'
            assert len(Domain.domains.all()) == 1

    def test_profile_is_not_complete(self):
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='https://ns1.google.com',
        ))
        assert response.status_code == 302
        assert response.url == '/profile/'

    @pytest.mark.django_db
    @mock.patch('django.contrib.messages.error')
    @mock.patch('back.models.profile.Profile.is_complete')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_zone_is_not_supported(self, mock_user_profile_complete, mock_messages_error):
        mock_user_profile_complete.return_value = True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person)
            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)
            response = self.client.post('/domains/create/test.ax/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id,
            ))
        assert response.status_code == 302
        assert response.url == '/domains/'
        mock_messages_error.assert_called_once()

    @mock.patch('socket.gethostbyname')
    @mock.patch('os.system')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=True)
    def test_nameserver_is_not_available(self, mock_ping, mock_gethostbyname):
        mock_ping.return_value = -1
        mock_gethostbyname.side_effect = socket.error('failed')
        tester = prepare_tester_account()
        contact_admin = prepare_tester_contact(tester=tester)
        profile = prepare_tester_profile(tester=tester)
        prepare_tester_registrant(tester=tester, profile_object=profile)
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='dns1.kuwaitnet.net',
            contact_admin=contact_admin.id,
        ))
        assert response.status_code == 200
        assert response.context['errors'] == ['List of nameservers that are not valid or not reachable at this '
                                              'moment: <br>dns1.kuwaitnet.net <br>Please try again later or '
                                              'specify valid and available nameservers.']

    @mock.patch('django.contrib.messages.error')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_glue_record_not_supported(self, mock_messages_error):
        tester = prepare_tester_account()
        contact_admin = prepare_tester_contact(tester=tester)
        profile = prepare_tester_profile(tester=tester)
        prepare_tester_registrant(tester=tester, profile_object=profile)
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='ns1.test.ai',
            contact_admin=contact_admin.id,
        ))
        assert response.status_code == 302
        mock_messages_error.assert_called_once()

    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_nameserver_is_not_valid(self):
        tester = prepare_tester_account()
        contact_admin = prepare_tester_contact(tester=tester)
        profile = prepare_tester_profile(tester=tester)
        prepare_tester_registrant(tester=tester, profile_object=profile)
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='1',
            contact_admin=contact_admin.id,
        ))
        assert response.status_code == 200
        assert response.context['errors'] == ['Please use correct DNS name for the nameservers.', ]

    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_nameserver_is_not_valid_with_two_dots(self):
        tester = prepare_tester_account()
        contact_admin = prepare_tester_contact(tester=tester)
        profile = prepare_tester_profile(tester=tester)
        prepare_tester_registrant(tester=tester, profile_object=profile)
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='1.2',
            contact_admin=contact_admin.id,
        ))
        assert response.status_code == 200
        assert response.context['errors'] == ['Please use DNS name instead of IP address for the nameservers.', ]


class TestAccountDomainUpdateView(BaseAuthTesterMixin, TestCase):

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_update_successful_e2e(self, mock_user_profile_complete):
        if os.environ.get('E2E', '0') != '1':
            return pytest.skip('skip E2E')  # @UndefinedVariable
        mock_user_profile_complete.return_value = True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            # First create a contact person for the owner
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            # 2nd create a domain
            created_domain = Domain.domains.create(
                owner=self.account,
                name='test.ai',
                expiry_date=datetime.datetime(2099, 1, 1),
                create_date=datetime.datetime(1970, 1, 1),
                zone=Zone.zones.create(name='ai'),
                epp_id='12345',
            )
            # 3rd update the domain
            response = self.client.post(f'/domains/edit/{created_domain.id}/', data=dict(
                nameserver1='ns2.google.com',
                contact_tech=Contact.contacts.all()[0].id,
            ))
            assert response.status_code == 302
            assert response.url == '/domains/'

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_update_domain_of_other_user(self, mock_user_profile_complete):
        mock_user_profile_complete.return_value = True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            response = self.client.post('/domains/edit/3/', data=dict(
                nameserver1='ns2.google.com',
                contact_tech=Contact.contacts.all()[0].id,
            ))
            assert response.status_code == 404

    def test_profile_is_not_complete(self):
        response = self.client.post('/domains/edit/1/', data=dict(
            nameserver1='https://ns1.google.com',
        ))
        assert response.status_code == 302
        assert response.url == '/profile/'

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_contact_info_is_not_complete(self, mock_user_profile_complete):
        mock_user_profile_complete.return_value = True
        response = self.client.post('/domains/edit/1/', data=dict(
            nameserver1='https://ns1.google.com',
        ))
        assert response.status_code == 404

    @mock.patch('zen.zmaster.contact_create_update')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('socket.gethostbyname')
    @mock.patch('os.system')
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    def test_nameserver_is_not_available(
        self, mock_epp_call, mock_ping, mock_gethostbyname, mock_user_profile_complete, mock_contact_create_update,
    ):
        mock_epp_call.return_value = True
        mock_ping.return_value = -1
        mock_gethostbyname.side_effect = socket.error('failed')
        mock_user_profile_complete.return_value = True
        # Create a contact person to have a domain.
        mock_contact_create_update.return_value = True
        self.client.post('/contacts/create/', data=contact_person, follow=True)
        # Create a domain.
        created_domain = Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
        )
        # Update the domain.
        response = self.client.post(f'/domains/edit/{created_domain.id}/', data=dict(
            nameserver1='dns1.kuwaitnet.net',
            contact_tech=Contact.contacts.all()[0].id,
        ))
        assert response.status_code == 200
        assert response.context['errors'] == ['List of nameservers that are not valid or not reachable at this '
                                              'moment: <br>dns1.kuwaitnet.net <br>Please try again later or '
                                              'specify valid and available nameservers.']

    @mock.patch('zen.zmaster.contact_create_update')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    def test_nameserver_is_wrong(
        self, mock_epp_call, mock_user_profile_complete, mock_contact_create_update
    ):
        mock_epp_call.return_value = True
        mock_user_profile_complete.return_value = True
        # Create a contact person to have a domain.
        mock_contact_create_update.return_value = True
        self.client.post('/contacts/create/', data=contact_person, follow=True)
        # Create a domain.
        created_domain = Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            nameserver1='ns1.example.com',
        )
        # Update the domain with an ip address.
        response = self.client.post(f'/domains/edit/{created_domain.id}/', data=dict(
            nameserver1='8.8.8.8',
            contact_tech=Contact.contacts.all()[0].id,
        ))
        assert response.status_code == 200
        domain = Domain.domains.all()[0]
        assert domain.nameserver1 == 'ns1.example.com'
        # Update the domain with an ip address with spaces.
        response = self.client.post(f'/domains/edit/{created_domain.id}/', data=dict(
            nameserver1=' 8.8.8.8 ',
            contact_tech=Contact.contacts.all()[0].id,
        ))
        assert response.status_code == 200
        domain = Domain.domains.all()[0]
        assert domain.nameserver1 == 'ns1.example.com'

    @mock.patch('zen.zmaster.contact_create_update')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    def test_glue_record(
        self, mock_epp_call, mock_user_profile_complete, mock_contact_create_update
    ):
        mock_epp_call.return_value = True
        mock_user_profile_complete.return_value = True
        # Create a contact person to have a domain.
        mock_contact_create_update.return_value = True
        self.client.post('/contacts/create/', data=contact_person, follow=True)
        # Create a domain.
        created_domain = Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            nameserver1='ns1.example.com',
        )
        # Update the domain with a "glue" record
        response = self.client.post(f'/domains/edit/{created_domain.id}/', data=dict(
            nameserver1='ns1.test.ai',
            contact_tech=Contact.contacts.all()[0].id,
        ))
        assert response.status_code == 200
        assert response.context['errors'] == ['Please use another nameserver instead of ns1.test.ai, "glue" records are not supported yet.']
        domain = Domain.domains.all()[0]
        assert domain.nameserver1 == 'ns1.example.com'


class TestAccountDomainTransferCodeView(BaseAuthTesterMixin, TestCase):
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_set_auth_info')
    def test_get_successful_transfer_code(self, mock_set_auth_info, mock_user_profile_complete, mock_list_contacts):
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock()]
        domain = Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            auth_key='transfer_me',
        )
        response = self.client.get(f'/domains/{domain.id}/transfer-code/')
        assert response.status_code == 200
        assert response.context_data['transfer_code'] == 'transfer_me'
        assert response.context_data['domain_name'] == 'test.ai'

    @mock.patch('django.contrib.messages.error')
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_set_auth_info')
    def test_technical_error(
        self, mock_set_auth_info, mock_user_profile_complete, mock_list_contacts, mock_messages_error,
    ):
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock()]
        mock_set_auth_info.return_value = False
        domain = Domain.domains.create(
            owner=self.account,
            name='test.ai',
            expiry_date=datetime.datetime(2099, 1, 1),
            create_date=datetime.datetime(1970, 1, 1),
            zone=Zone.zones.create(name='ai'),
            epp_id='12345',
            auth_key='transfer_me',
        )
        response = self.client.get(f'/domains/{domain.id}/transfer-code/')
        assert response.status_code == 302
        assert response.url == '/domains/'
        mock_messages_error.assert_called_once()


class TestAccountDomainTransferTakeoverView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_takeover_successful(
        self, mock_domain_info, mock_user_profile_complete, mock_list_contacts
    ):
        mock_domain_info.return_value = [{
            "epp": {
                "response": {
                    "resData": {
                        "infData": {
                            "clID": "12345",
                            "status": {
                                "@s": "Good",
                            },
                            "authInfo": {
                                "pw": "Authinfo Correct",
                            }
                        }
                    }
                }
            }
        }, {
            'bitdust.ai': True,
        }, ]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock(), ]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        order = billing_orders.list_orders(owner=self.account)[0]
        assert order.owner == self.account
        assert response.status_code == 302
        assert response.url == f'/billing/order/{order.id}/'
        order = billing_orders.list_orders(owner=self.account)[0]
        assert order.owner == self.account
        order_item = order.items.all()[0]
        assert order_item.type == 'domain_transfer'
        assert order_item.price == 100.0
        assert order_item.name == 'bitdust.ai'
        assert order_item.details == {'transfer_code': '12345', 'rewrite_contacts': True, 'internal': False}

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @override_settings(ZENAIDA_REGISTRAR_ID='test_registrar')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_takeover_internal_successful(
        self, mock_domain_info, mock_user_profile_complete, mock_list_contacts
    ):
        mock_domain_info.return_value = [{
            "epp": {
                "response": {
                    "resData": {
                        "infData": {
                            "clID": "test_registrar",
                            "status": {
                                "@s": "Good",
                            },
                            "authInfo": {
                                "pw": "Authinfo Correct",
                            }
                        }
                    }
                }
            }
        }, {
            'bitdust.ai': True,
        }, ]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock(), ]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        order = billing_orders.list_orders(owner=self.account)[0]
        assert order.owner == self.account
        assert response.status_code == 302
        assert response.url == f'/billing/order/{order.id}/'
        order_item = order.items.all()[0]
        assert order_item.type == 'domain_transfer'
        assert order_item.price == 0.0
        assert order_item.name == 'bitdust.ai'
        assert order_item.details == {'transfer_code': '12345', 'rewrite_contacts': True, 'internal': True}

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @mock.patch('django.contrib.messages.error')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_not_possible_backend_down(
        self, mock_messages_error, mock_domain_info, mock_user_profile_complete, mock_list_contacts,
    ):
        mock_domain_info.return_value = [
            rpc_error.EPPCommandFailed(),
        ]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock()]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        assert response.status_code == 200
        mock_messages_error.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @mock.patch('django.contrib.messages.error')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_not_authorized(
        self, mock_messages_error, mock_domain_info, mock_user_profile_complete, mock_list_contacts,
    ):
        mock_domain_info.return_value = [
            rpc_error.EPPAuthorizationError(),
        ]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock()]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        assert response.status_code == 200
        mock_messages_error.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @mock.patch('django.contrib.messages.warning')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_not_registered(
        self, mock_messages_warning, mock_domain_info, mock_user_profile_complete, mock_list_contacts,
    ):
        mock_domain_info.return_value = [{
            'bitdust.ai': False,
        }, ]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock()]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        assert response.status_code == 200
        mock_messages_warning.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @mock.patch('django.contrib.messages.error')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_auth_info_wrong(
        self, mock_messages_error, mock_domain_info, mock_user_profile_complete, mock_list_contacts,
    ):
        mock_domain_info.return_value = [{
            "epp": {
                "response": {
                    "resData": {
                        "infData": {
                            "clID": "12345",
                            "status": {
                                "@s": "Good",
                            },
                            "authInfo": {
                                "pw": "Authinfo Not Correct",
                            }
                        }
                    }
                }
            }
        }, {
            'bitdust.ai': True,
        }, ]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock(), ]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        assert response.status_code == 200
        mock_messages_error.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @mock.patch('django.contrib.messages.error')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_is_prohibited(
        self, mock_messages_error, mock_domain_info, mock_user_profile_complete, mock_list_contacts,
    ):
        mock_domain_info.return_value = [{
            "epp": {
                "response": {
                    "resData": {
                        "infData": {
                            "clID": "12345",
                            "status": {
                                "@s": "serverTransferProhibited",
                            },
                            "authInfo": {
                                "pw": "Authinfo Correct",
                            }
                        }
                    }
                }
            }
        }, {
            'bitdust.ai': True,
        }]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock(), ]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        assert response.status_code == 200
        mock_messages_error.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zmaster.domain_read_info')
    @mock.patch('django.contrib.messages.warning')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_transfer_takeover_already_in_progress(
        self, mock_messages_warning, mock_domain_info, mock_user_profile_complete, mock_list_contacts,
    ):
        started_order = billing_orders.order_single_item(
            owner=self.account,
            item_type="domain_transfer",
            item_price=100.0,
            item_name="bitdust.ai",
        )
        started_order_item = started_order.items.all()[0]
        billing_orders.update_order_item(order_item=started_order_item, new_status='pending')
        mock_domain_info.return_value = [{
            "epp": {
                "response": {
                    "resData": {
                        "infData": {
                            "clID": "12345",
                            "status": {
                                "@s": "Good",
                            },
                            "authInfo": {
                                "pw": "Authinfo Correct",
                            }
                        }
                    }
                }
            }
        }, {
            'bitdust.ai': True,
        }, ]
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock(), ]
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        assert response.status_code == 200
        mock_messages_warning.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.list_contacts')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('django.contrib.messages.error')
    @mock.patch('django.core.cache.cache.get')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=True)
    def test_domain_transfer_too_many_attempts(self, mock_cache_get, mock_messages_error, mock_user_profile_complete, mock_list_contacts):
        mock_user_profile_complete.return_value = True
        mock_list_contacts.return_value = [mock.MagicMock(), mock.MagicMock(), ]
        mock_cache_get.return_value = settings.BRUTE_FORCE_PROTECTION_DOMAIN_TRANSFER_MAX_ATTEMPTS
        response = self.client.post('/domains/transfer/', data=dict(domain_name='bitdust.ai', transfer_code='12345'))
        assert response.status_code == 200
        mock_messages_error.assert_called_once()


class TestAccountProfileView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_get_profile(self):
        response = self.client.get('/profile/')
        assert response.status_code == 200
        assert isinstance(response.context['object'], Profile) is True

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.contact_create_from_profile')
    @mock.patch('zen.zmaster.contact_create_update')
    @mock.patch('django.contrib.messages.success')
    def test_create_profile_with_contact_person(
        self, mock_messages_success, mock_contact_create_update, mock_contact_create_from_profile,
    ):
        response = self.client.post('/profile/', data=contact_person, follow=True)
        assert response.status_code == 200
        assert mock_contact_create_update.call_count == 2
        mock_contact_create_from_profile.assert_called_once()
        mock_messages_success.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zcontacts.contact_create_from_profile')
    @mock.patch('zen.zmaster.contact_create_update')
    @mock.patch('django.contrib.messages.error')
    def test_create_profile_with_contact_person_returns_error(
        self, mock_messages_error, mock_contact_create_update, mock_contact_create_from_profile,
    ):
        mock_contact_create_update.return_value = False
        response = self.client.post('/profile/', data=contact_person, follow=True)
        assert response.status_code == 200
        mock_contact_create_update.assert_called_once()
        mock_contact_create_from_profile.assert_called_once()
        mock_messages_error.assert_called_once()

    @pytest.mark.django_db
    def test_create_profile_non_ascii_validation_error(self):
        contact = copy.deepcopy(contact_person)
        contact['address_city'] = 'Mońki'
        response = self.client.post('/profile/', data=contact, follow=True)
        assert response.status_code == 200
        assert response.context['errors'] == ['Please use only English characters in your details.', ]


class TestAccountContactCreateView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_create_db_successful(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            response = self.client.post('/contacts/create/', data=contact_person, follow=True)
            assert response.status_code == 200
            c = contact.Contact.contacts.filter(person_name='TesterA').first()
            assert c.person_name == 'TesterA'

    @pytest.mark.django_db
    def test_contact_create_update_error(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = False
            response = self.client.post('/contacts/create/', data=contact_person, follow=True)
            assert response.status_code == 200
            assert contact.Contact.contacts.filter(person_name='TesterA').first() is None

    @pytest.mark.django_db
    def test_contact_info_create_non_ascii_validation_error(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            contact = copy.deepcopy(contact_person)
            contact['address_city'] = 'Mońki'
            response = self.client.post('/contacts/create/', data=contact, follow=True)
            assert response.status_code == 200
            assert response.context['errors'] == ['Please use only English characters in your details.', ]


class TestAccountContactUpdateView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_update_db_successful(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            # First create contact person
            self.client.post('/contacts/create/', data=contact_person)
        # Check if contact person is created successfully with given data
        c = contact.Contact.contacts.filter(person_name='TesterA').first()
        assert c.person_name == 'TesterA'
        # Update the contact person
        updated_contact_person = copy.deepcopy(contact_person)
        updated_contact_person['person_name'] = 'TesterB'
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            response = self.client.post('/contacts/edit/%d/' % c.id, data=updated_contact_person)
        assert response.status_code == 302
        assert response.url == '/contacts/'
        # Check if contact person is updated successfully
        c = contact.Contact.contacts.all()[0]
        assert c.person_name == 'TesterB'

    @pytest.mark.django_db
    def test_contact_info_update_non_ascii_validation_error(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            contact = copy.deepcopy(contact_person)
            contact['address_city'] = 'Mońki'
            response = self.client.post('/contacts/create/', data=contact, follow=True)
            assert response.status_code == 200
            assert response.context['errors'] == ['Please use only English characters in your details.', ]

    def test_contact_update_returns_404(self):
        response = self.client.put('/contacts/edit/1/')
        assert response.status_code == 404


class TestAccountContactDeleteView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_contact_delete_successful(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            # First create contact person
            self.client.post('/contacts/create/', data=contact_person)
        # Check if contact person is created successfully with given data
        c = contact.Contact.contacts.filter(person_name='TesterA').first()
        assert c.person_name == 'TesterA'
        # Check if contact list is empty after deletion
        response = self.client.delete('/contacts/delete/%d/' % c.id)
        assert response.status_code == 302
        assert response.url == '/contacts/'
        assert len(contact.Contact.contacts.all()) == 0

    def test_contact_delete_returns_404(self):
        response = self.client.delete('/contacts/delete/1/')
        # User has not this contact, so can't delete
        assert response.status_code == 404


class TestAccountContactsListView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    def test_contact_list_successful(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            # First create contact_person
            self.client.post('/contacts/create/', data=contact_person)
        response = self.client.get('/contacts/')
        assert response.status_code == 200
        assert len(contact.Contact.contacts.all()) == 1

    @pytest.mark.django_db
    def test_contact_list_empty(self):
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
        response = self.client.get('/contacts/')
        assert response.status_code == 200
        assert len(contact.Contact.contacts.all()) == 0


class TestDomainLookupView(TestCase):

    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_e2e_successful(self):
        if os.environ.get('E2E', '0') != '1':
            return pytest.skip('skip E2E')  # @UndefinedVariable
        response = self.client.post('/lookup/', data=dict(domain_name='Bitdust123.ai'))
        assert response.status_code == 200
        assert response.context['result'] == 'not exist'
        assert response.context['domain_name'] == 'bitdust123.ai'

    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_e2e_domain_exists(self):
        if os.environ.get('E2E', '0') != '1':
            return pytest.skip('skip E2E')  # @UndefinedVariable
        response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 200
        assert response.context['result'] == 'exist'
        assert response.context['domain_name'] == 'test.ai'

    @mock.patch('django.contrib.messages.error')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_lookup_returns_error(self, mock_messages_error):
        with mock.patch('zen.zmaster.domains_check') as mock_domain_check:
            mock_domain_check.return_value = None
            response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 200
        assert response.context['domain_name'] == 'bitdust.ai'
        mock_messages_error.assert_called_once()

    @mock.patch('django.contrib.messages.warning')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_is_already_in_db(self, mock_messages_warning):
        with mock.patch('zen.zdomains.is_domain_available') as mock_is_domain_available:
            mock_is_domain_available.return_value = False
            response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 200
        assert response.context['domain_name'] == 'bitdust.ai'
        mock_messages_warning.assert_called_once()

    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_lookup_page_without_domain_name(self):
        response = self.client.post('/lookup/')
        assert response.status_code == 200

    @mock.patch('django.contrib.messages.error')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_lookup_with_invalid_domain_name(self, mock_messages_error):
        response = self.client.post('/lookup/', data=dict(domain_name='example'))
        assert response.status_code == 200
        assert response.context['domain_name'] == 'example'
        mock_messages_error.assert_called_once()

    @mock.patch('django.contrib.messages.error')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=False)
    def test_domain_lookup_with_invalid_domain_extension(self, mock_messages_error):
        response = self.client.post('/lookup/', data=dict(domain_name='example.xyz'))
        assert response.status_code == 200
        assert response.context['domain_name'] == 'example.xyz'
        assert response.context['result'] is None
        mock_messages_error.assert_called_once()

    @mock.patch('django.contrib.messages.error')
    @mock.patch('django.core.cache.cache.get')
    @override_settings(BRUTE_FORCE_PROTECTION_ENABLED=True)
    def test_domain_lookup_too_many_attempts(self, mock_cache_get, mock_messages_error):
        mock_cache_get.return_value = settings.BRUTE_FORCE_PROTECTION_DOMAIN_TRANSFER_MAX_ATTEMPTS
        response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 302
        assert response.url == '/lookup/'
        mock_messages_error.assert_called_once()


class TestEPPStatusViewView(BaseAuthTesterMixin, TestCase):

    @mock.patch('front.views.EPPStatusView.check_epp_status')
    @mock.patch('django.core.cache.cache.get')
    def test_healthy(self, mock_cache_get, mock_check_epp_status):
        mock_cache_get.return_value = None
        mock_check_epp_status.return_value = 'OK'
        response = self.client.get(f'/epp-status/')
        assert response.status_code == 200

    @mock.patch('front.views.EPPStatusView.check_epp_status')
    @mock.patch('django.core.cache.cache.get')
    def test_healthy_cached(self, mock_cache_get, mock_check_epp_status):
        mock_cache_get.return_value = 'OK'
        mock_check_epp_status.assert_not_called()
        response = self.client.get(f'/epp-status/')
        assert response.status_code == 200

    @mock.patch('front.views.EPPStatusView.check_epp_status')
    @mock.patch('django.core.cache.cache.get')
    def test_unhealthy(self, mock_cache_get, mock_check_epp_status):
        mock_cache_get.return_value = None
        mock_check_epp_status.return_value = 'some error'
        response = self.client.get(f'/epp-status/')
        assert response.status_code == 500

    @mock.patch('front.views.EPPStatusView.check_epp_status')
    @mock.patch('django.core.cache.cache.get')
    def test_unhealthy_cached(self, mock_cache_get, mock_check_epp_status):
        mock_cache_get.return_value = 'previous'
        mock_check_epp_status.assert_not_called()
        response = self.client.get(f'/epp-status/')
        assert response.status_code == 500


class TestFAQViews(TestCase):

    def test_faq_successful(self):
        response = self.client.get('/faq/')
        assert response.status_code == 200


class TestEscrowViews(TestCase):

    def test_escrow_successful(self):
        response = self.client.get('/escrow/')
        assert response.status_code == 200


class TemplateContactUsTemplateView(TestCase):

    def test_contact_us_successful(self):
        response = self.client.get('/contact-us/')
        assert response.status_code == 200


class TestErrorViews(BaseAuthTesterMixin, TestCase):

    def test_404_handler(self):
        with mock.patch('back.models.profile.Profile.is_complete') as mock_user_profile_complete:
            mock_user_profile_complete.return_value = True
            response = self.client.post('/contacts/edit/12345/')
            assert response.status_code == 404

    def test_403_handler(self):
        response = self.client.get('/not/exist.html')
        assert response.status_code == 403
