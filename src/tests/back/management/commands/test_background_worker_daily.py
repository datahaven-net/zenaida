import pytest
from django.test import TestCase
from mock import mock

from back.management.commands.background_worker_daily import Command as DailyWorkerDjangoCommand, \
    sync_to_be_deleted_domains_from_backend
from tests.testsupport import prepare_tester_domain


class TestCommand(TestCase):
    @mock.patch('back.management.commands.background_worker_daily.sync_to_be_deleted_domains_from_backend')
    def test_django_command(self, mock_backend_sync):
        DailyWorkerDjangoCommand().handle()
        mock_backend_sync.assert_called_once()

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_sync_to_be_deleted_domains_from_backend(self, mock_backend_sync):
        prepare_tester_domain(domain_name='test.ai', domain_status='to_be_deleted')
        sync_to_be_deleted_domains_from_backend()
        mock_backend_sync.assert_called_once_with(
            domain_name='test.ai',
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=False,
            create_new_owner_allowed=False,
            soft_delete=True,
            raise_errors=True,
            log_events=True,
            log_transitions=True,
        )
