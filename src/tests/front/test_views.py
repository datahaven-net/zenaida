import os
import mock
import pytest

from django.test import TestCase

from back.models import contact

from zen import zusers


class BaseAuthTesterMixin(object):

    @pytest.mark.django_db
    def setUp(self):
        zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestAccountContactCreateView(BaseAuthTesterMixin, TestCase):

    test_data = {
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

    target_url = '/contacts/create/'

    @pytest.mark.django_db
    def test_e2e_success(self):
        if os.environ.get('E2E', '0') == '0':
            return True
        response = self.client.post(self.target_url, data=self.test_data, follow=True)
        self.assertEqual(response.status_code, 200)
        c = contact.Contact.contacts.filter(person_name='TesterA').first()
        self.assertEqual(c.person_name, 'TesterA')

    @pytest.mark.django_db
    def test_create_db_success(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = True
            response = self.client.post(self.target_url, data=self.test_data, follow=True)
            self.assertEqual(response.status_code, 200)
            c = contact.Contact.contacts.filter(person_name='TesterA').first()
            self.assertEqual(c.person_name, 'TesterA')

    @pytest.mark.django_db
    def test_contact_create_update_error(self):
        if os.environ.get('E2E', '0') == '1':
            return True
        with mock.patch('zen.zmaster.contact_create_update') as mock_contact_create_update:
            mock_contact_create_update.return_value = False
            response = self.client.post(self.target_url, data=self.test_data, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(contact.Contact.contacts.filter(person_name='TesterA').first())
