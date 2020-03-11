import copy
import datetime
import os
import mock
import pytest

from django.test import TestCase, override_settings

from back.models import contact
from back.models.contact import Contact, Registrant
from back.models.domain import Domain
from back.models.zone import Zone

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
            epp_id='12345'
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
        assert response.status_code == 302
        assert response.url == '/contacts/'


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

    def test_index_page_redirects_to_contacts_page(self):
        with mock.patch('back.models.profile.Profile.is_complete') as mock_user_profile_complete:
            response = self.client.get('')
        assert response.status_code == 302
        assert response.url == '/contacts/'


class TestIndexViewForUnknownUser(TestCase):

    def test_index_page_successful(self):
        response = self.client.get('')
        assert response.status_code == 200


class TestAccountDomainCreateView(BaseAuthTesterMixin, TestCase):

    @pytest.mark.django_db
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zzones.is_supported')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_create_domain_successful(self, mock_zone_is_supported, mock_user_profile_complete):
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
                contact_admin=Contact.contacts.all()[0].id
            ))

            assert response.status_code == 302
            assert len(Domain.domains.all()) == 1

    @pytest.mark.django_db
    @mock.patch('zen.zdomains.domain_find')
    @mock.patch('back.models.profile.Profile.is_complete')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_domain_is_already_registered(self, mock_user_profile_complete, mock_domain_find):
        mock_user_profile_complete.return_value = True
        mock_domain_find.return_value = mock.MagicMock(
            epp_id='12345'
        )

        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)

            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)

            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id
            ))

            assert response.status_code == 302
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
            create_date=datetime.datetime.utcnow()
        )
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)
            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)
            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id
            ))
            assert response.status_code == 302
            assert len(Domain.domains.all()) == 0

    @pytest.mark.django_db
    @mock.patch('zen.zdomains.domain_find')
    @mock.patch('back.models.profile.Profile.is_complete')
    @mock.patch('zen.zzones.is_supported')
    @override_settings(ZENAIDA_PING_NAMESERVERS_ENABLED=False)
    def test_domain_is_available_after_1_hour(
        self, mock_zone_is_supported, mock_user_profile_complete, mock_domain_find
    ):
        """
        Test after domain was someone's basket for an hour, user can still register it.
        """
        mock_zone_is_supported.return_value = True
        mock_user_profile_complete.return_value = True
        mock_domain_find.return_value = mock.MagicMock(
            epp_id=None,
            create_date=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            id=1
        )

        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            self.client.post('/contacts/create/', data=contact_person, follow=True)

            registrant_info = copy.deepcopy(contact_person)
            registrant_info['owner'] = zusers.find_account('tester@zenaida.ai')
            Registrant.registrants.create(**registrant_info)

            response = self.client.post('/domains/create/test.ai/', data=dict(
                nameserver1='ns1.google.com',
                contact_admin=Contact.contacts.all()[0].id
            ))

            assert response.status_code == 302
            assert len(Domain.domains.all()) == 1

    def test_profile_is_not_complete(self):
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='https://ns1.google.com'
        ))

        assert response.status_code == 302
        assert response.url == '/profile/'

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_contact_info_is_not_complete(self, mock_user_profile_complete):
        response = self.client.post('/domains/create/test.ai/', data=dict(
            nameserver1='https://ns1.google.com'
        ))

        assert response.status_code == 302
        assert response.url == '/contacts/'

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
                contact_admin=Contact.contacts.all()[0].id
            ))

        assert response.status_code == 302
        assert response.url == '/domains/'
        mock_messages_error.assert_called_once()


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
                epp_id='12345'
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
            nameserver1='https://ns1.google.com'
        ))

        assert response.status_code == 302
        assert response.url == '/profile/'

    @mock.patch('back.models.profile.Profile.is_complete')
    def test_contact_info_is_not_complete(self, mock_user_profile_complete):
        mock_user_profile_complete.return_value = True

        response = self.client.post('/domains/edit/1/', data=dict(
            nameserver1='https://ns1.google.com'
        ))

        assert response.status_code == 302
        assert response.url == '/contacts/'


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
            auth_key='transfer_me'
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
        self, mock_set_auth_info, mock_user_profile_complete, mock_list_contacts, mock_messages_error
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
            auth_key='transfer_me'
        )

        response = self.client.get(f'/domains/{domain.id}/transfer-code/')

        assert response.status_code == 302
        assert response.url == '/domains/'
        mock_messages_error.assert_called_once()


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

    def test_e2e_successful(self):
        if os.environ.get('E2E', '0') != '1':
            return pytest.skip('skip E2E')  # @UndefinedVariable
        response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 200
        assert response.context['result'] == 'not exist'
        assert response.context['domain_name'] == 'bitdust.ai'

    def test_e2e_domain_exists(self):
        if os.environ.get('E2E', '0') != '1':
            return pytest.skip('skip E2E')  # @UndefinedVariable
        response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 200
        assert response.context['result'] == 'exist'
        assert response.context['domain_name'] == 'test.ai'

    def test_domain_lookup_returns_error(self):
        with mock.patch('zen.zmaster.domains_check') as mock_domain_check:
            mock_domain_check.return_value = None
            response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 200
        assert response.context['result'] == 'error'
        assert response.context['domain_name'] == 'bitdust.ai'

    def test_domain_is_already_in_db(self):
        with mock.patch('zen.zdomains.is_domain_available') as mock_is_domain_available:
            mock_is_domain_available.return_value = False
            response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 200
        assert response.context['result'] == 'exist'
        assert response.context['domain_name'] == 'bitdust.ai'

    def test_domain_lookup_page_without_domain_name(self):
        response = self.client.post('/lookup/')
        assert response.status_code == 200

    @mock.patch('django.contrib.messages.error')
    def test_domain_lookup_with_invalid_domain_name(self, mock_messages_error):
        response = self.client.post('/lookup/', data=dict(domain_name='example'))
        assert response.status_code == 200
        assert response.context['domain_name'] == 'example'
        assert response.context['result'] is None
        mock_messages_error.assert_called_once()

    @mock.patch('django.contrib.messages.error')
    def test_domain_lookup_with_invalid_domain_extension(self, mock_messages_error):
        response = self.client.post('/lookup/', data=dict(domain_name='example.xyz'))
        assert response.status_code == 200
        assert response.context['domain_name'] == 'example.xyz'
        assert response.context['result'] is None
        mock_messages_error.assert_called_once()

    @override_settings(BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_MAX_ATTEMPTS=2, BRUTE_FORCE_PROTECTION_ENABLED=True)
    @mock.patch('django.contrib.messages.error')
    @mock.patch('django.core.cache.cache.get')
    def test_domain_lookup_too_many_attempts(self, mock_cache_get, mock_messages_error):
        mock_cache_get.return_value = 2
        response = self.client.post('/lookup/', data=dict(domain_name='bitdust.ai'))
        assert response.status_code == 302
        assert response.url == '/lookup/'
        mock_messages_error.assert_called_once()


class TestFAQViews(TestCase):

    def test_faq_successful(self):
        response = self.client.get('/faq/')
        assert response.status_code == 200


class TemplateContactUsTemplateView(TestCase):

    def test_contact_us_successful(self):
        response = self.client.get('/contact-us/')
        assert response.status_code == 200
