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

    target_url = '/contacts/create/'

    @pytest.mark.django_db
    def test_e2e_success(self):
        if os.environ.get('E2E', '0') == '0':
            return True
        response = self.client.post(self.target_url, data=contact_person, follow=True)
        assert response.status_code == 200
        c = contact.Contact.contacts.filter(person_name='TesterA').first()
        assert c.person_name == 'TesterA'

    @pytest.mark.django_db
    def test_create_db_success(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            response = self.client.post(self.target_url, data=contact_person, follow=True)
            assert response.status_code == 200
            c = contact.Contact.contacts.filter(person_name='TesterA').first()
            assert c.person_name == 'TesterA'

    @pytest.mark.django_db
    def test_contact_create_update_error(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = False
            response = self.client.post(self.target_url, data=contact_person, follow=True)
            assert response.status_code == 200
            assert contact.Contact.contacts.filter(person_name='TesterA').first() is None


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
