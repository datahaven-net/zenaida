import datetime
import mock
import pytest

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from tests import testsupport


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = testsupport.prepare_tester_account(
            is_staff=True,
            join_date=datetime.datetime(2019, 1, 1, 1, 0, 0)
        )
        self.client.login(email='tester@zenaida.ai', password='tester')


class TestFinancialReportView(BaseAuthTesterMixin, TestCase):
    def test_financial_result_for_specific_month_successful(self):
        testsupport.prepare_tester_order(
            domain_name='test.ai',
            status='processed',
            finished_at=datetime.datetime(2019, 1, 1, 1, 0, 0),
            owner=self.account
        )
        response = self.client.post('/board/financial-report/', data=dict(year=2019, month=1))

        assert response.status_code == 200
        assert response.context['total_payment_by_users'] == 100.0
        assert response.context['total_registered_users'] == 1
        assert len(response.context['object_list']) == 1

    def test_financial_result_for_specific_year_successful(self):
        testsupport.prepare_tester_order(
            domain_name='test1.ai',
            status='processed',
            finished_at=datetime.datetime(2019, 1, 1, 1, 0, 0),
            owner=self.account
        )
        testsupport.prepare_tester_order(
            domain_name='test2.ai',
            status='processed',
            finished_at=datetime.datetime(2019, 2, 1, 1, 0, 0),
            owner=self.account
        )

        response = self.client.post('/board/financial-report/', data=dict(year=2019))

        assert response.status_code == 200
        assert response.context['total_payment_by_users'] == 200.0
        assert response.context['total_registered_users'] == 1
        assert len(response.context['object_list']) == 2

    @mock.patch('django.contrib.messages.error')
    def test_financial_result_access_denied_for_normal_user(self, mock_messages_error):
        self.account.is_staff = False
        self.account.save()
        testsupport.prepare_tester_order(
            domain_name='test3.ai',
            status='processed',
            finished_at=datetime.datetime(2019, 1, 1, 1, 0, 0),
            owner=self.account
        )

        response = self.client.post('/board/financial-report/', data=dict(year=2019))

        assert response.status_code == 302
        assert response.url == '/'
        mock_messages_error.assert_called_once()


class TestNotExistingDomainSyncView(BaseAuthTesterMixin, TestCase):
    @mock.patch('django.contrib.messages.success')
    @mock.patch('zen.zdomains.domain_find')
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_domain_sync_successful(self, mock_sync_backend, mock_domain_find, mock_messages_success):
        self.client.post('/board/domain-sync/', data=dict(domain_name='test.ai'))
        mock_sync_backend.assert_called_once()
        mock_domain_find.assert_called_once_with(domain_name='test.ai')
        mock_messages_success.assert_called_once()

    @mock.patch('django.contrib.messages.warning')
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_domain_sync_not_successful(self, mock_sync_backend, mock_messages_warning):
        self.client.post('/board/domain-sync/', data=dict(domain_name='test.ai'))
        mock_sync_backend.assert_called_once()
        mock_messages_warning.assert_called_once()

    @mock.patch('django.contrib.messages.error')
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_domain_sync_access_denied_for_normal_user(self, mock_sync_backend, mock_messages_error):
        self.account.is_staff = False
        self.account.save()

        response = self.client.post('/board/domain-sync/', data=dict(domain_name='test.ai'))

        assert response.url == '/'
        mock_sync_backend.assert_not_called()
        mock_messages_error.assert_called_once()


class TestCSVFileSyncView(BaseAuthTesterMixin, TestCase):

    @mock.patch('django.contrib.messages.error')
    def test_access_denied_for_normal_user(self, mock_messages_error):
        self.account.is_staff = False
        self.account.save()
        response = self.client.post('/board/csv-file-sync/', data=dict())
        assert response.url == '/'
        mock_messages_error.assert_called_once()

    @mock.patch('board.views.load_from_csv')
    def test_csv_file_upload_success(self, mock_load_from_csv):
        mock_load_from_csv.return_value = 100
        csv_file = SimpleUploadedFile("domains.csv", b"some_text_here", content_type="text/csv")
        response = self.client.post('/board/csv-file-sync/', {'csv_file': csv_file, 'dry_run': True, })
        mock_load_from_csv.assert_called_once()
        assert response.content.count(b'total records processed: 100') == 1
