import pytest
from django.test import TestCase

from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestStaffRequiredMixin(BaseAuthTesterMixin, TestCase):
    def test_user_is_staff(self):
        self.account.is_staff = True
        self.account.save()
        response = self.client.post('/board/financial-report/', data=dict(year=2019, month=1))
        assert response.status_code == 200

    def test_user_is_not_staff(self):
        response = self.client.post('/board/financial-report/', data=dict(year=2019, month=1))
        assert response.status_code == 302
        assert response.url == '/'
