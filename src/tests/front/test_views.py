import copy
import os
import mock
import pytest

from django.test import TestCase

from back.models import contact

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
        zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class AccountDomainsListView(BaseAuthTesterMixin, TestCase):
    pass


class TestIndexViewForLoggedInUser(BaseAuthTesterMixin, TestCase):
    def test_index_page_successful(self):
        with mock.patch('back.models.profile.Profile.is_complete') as mock_user_profile_complete:
            mock_user_profile_complete.return_value = True
            response = self.client.get('')
        assert response.status_code == 200
        assert response.context['total_domains'] == 0

    def test_index_page_redirects_to_profile_page(self):
        response = self.client.get('')
        assert response.status_code == 302
        assert response.url == '/profile/'


class TestIndexViewForUnknownUser(TestCase):
    def test_index_page_successful(self):
        response = self.client.get('')
        assert response.status_code == 200


class TestAccountContactCreateView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_e2e_successful(self):
        if os.environ.get('E2E', '0') == '0':
            return True
        response = self.client.post('/contacts/create/', data=contact_person, follow=True)
        assert response.status_code == 200
        c = contact.Contact.contacts.filter(person_name='TesterA').first()
        assert c.person_name == 'TesterA'

    @pytest.mark.django_db
    def test_create_db_successful(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            response = self.client.post('/contacts/create/', data=contact_person, follow=True)
            assert response.status_code == 200
            c = contact.Contact.contacts.filter(person_name='TesterA').first()
            assert c.person_name == 'TesterA'

    @pytest.mark.django_db
    def test_contact_create_update_error(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = False
            response = self.client.post('/contacts/create/', data=contact_person, follow=True)
            assert response.status_code == 200
            assert contact.Contact.contacts.filter(person_name='TesterA').first() is None


class TestAccountContactUpdateView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_e2e_successful(self):
        if os.environ.get('E2E', '0') == '0':
            return True
        updated_contact_person = copy.deepcopy(contact_person)
        updated_contact_person['person_name'] = 'TesterB'
        response = self.client.post('/contacts/edit/1/', data=updated_contact_person)
        assert response.status_code == 200
        c = contact.Contact.contacts.all()[0]
        assert c.person_name == 'TesterB'

    @pytest.mark.django_db
    def test_update_db_successful(self):
        if os.environ.get('E2E', '0') == '1':
            return True
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
        response = self.client.post('/contacts/edit/1/', data=updated_contact_person)

        assert response.status_code == 302
        assert response.url == '/contacts/'
        # Check if contact person is updated successfully
        c = contact.Contact.contacts.all()[0]
        assert c.person_name == 'TesterB'

    def test_contact_update_returns_404(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        response = self.client.put('/contacts/edit/1/')
        assert response.status_code == 404


class TestAccountContactDeleteView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_contact_delete_successful(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            # First create contact person
            self.client.post('/contacts/create/', data=contact_person)
        # Check if contact is created on DB
        assert len(contact.Contact.contacts.all()) == 1
        response = self.client.delete('/contacts/delete/1/')
        assert response.status_code == 302
        assert response.url == '/contacts/'
        # Check if contact list is empty after deletion
        assert len(contact.Contact.contacts.all()) == 0

    def test_contact_delete_returns_404(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        response = self.client.delete('/contacts/delete/1/')
        # User has not this contact, so can't delete
        assert response.status_code == 404


class TestAccountContactsListView(BaseAuthTesterMixin, TestCase):
    @pytest.mark.django_db
    def test_contact_list_successful(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            # First create contact_person
            self.client.post('/contacts/create/', data=contact_person)

        response = self.client.get('/contacts/')
        assert response.status_code == 200
        assert len(contact.Contact.contacts.all()) == 1

    @pytest.mark.django_db
    def test_contact_list_empty(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True

        response = self.client.get('/contacts/')
        assert response.status_code == 200
        assert len(contact.Contact.contacts.all()) == 0


class TestFAQViews(TestCase):
    def test_faq_successful(self):
        response = self.client.get('/faq/')
        assert response.status_code == 200

    def test_faq_epp_successful(self):
        response = self.client.get('/faq-epp/')
        assert response.status_code == 200

    def test_faq_auctions_successful(self):
        response = self.client.get('/faq-auctions/')
        assert response.status_code == 200

    def test_faq_payments_successful(self):
        response = self.client.get('/faq-payments/')
        assert response.status_code == 200

    def test_faq_correspondentbank_successful(self):
        response = self.client.get('/faq-correspondentbank/')
        assert response.status_code == 200

    def test_faq_registrars_successful(self):
        response = self.client.get('/faq-registrars/')
        assert response.status_code == 200


class TemplateContactUsTemplateView(TestCase):
    def test_contact_us_successful(self):
        response = self.client.get('/contact-us/')
        assert response.status_code == 200
