import mock
import pytest
import datetime

from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from tests import testsupport

from accounts.models.notification import Notification
from accounts.notifications import process_notifications_queue
from back import tasks
from back.models.back_end_renew import BackEndRenew
from billing import orders
from epp import rpc_error
from zen import zdomains
from zen import zmaster


class TestSyncExpiredDomains(TestCase):

    @pytest.mark.django_db
    def test_dry_run(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=True)
        assert len(report) == 1
        assert report[0] == (tester_domain, [], )

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_ok(self, mock_domain_synchronize_from_backend):
        mock_domain_synchronize_from_backend.return_value = ['ok', ]
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=False)
        assert len(report) == 1
        assert report[0] == (tester_domain, ['ok', ], )

    @pytest.mark.django_db
    def test_skip_not_expired(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=1)  # not expired yet
        tester_domain.status = 'active'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=False)
        assert len(report) == 0

    @pytest.mark.django_db
    def test_skip_not_active(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=1)  # already expired a day ago
        tester_domain.status = 'inactive'
        tester_domain.save()
        report = tasks.sync_expired_domains(dry_run=False)
        assert len(report) == 0


class TestBackEndAutoRenewExpiringDomains(TestCase):

    @pytest.mark.django_db
    @mock.patch('accounts.notifications.EmailMultiAlternatives.send')
    def test_order_created_executed_email_sent(self, mock_send):
        mock_send.return_value = True
        tester = testsupport.prepare_tester_account(account_balance=1000.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            # domain was already synchronized from back-end with the new expiry date
            expiry_date=timezone.now() + datetime.timedelta(days=45) + datetime.timedelta(days=365*2),
            auto_renew_enabled=True,
        )
        zmaster.create_back_end_renew_notification(
            domain_name='abcd.ai',
            previous_expiry_date=timezone.now() + datetime.timedelta(days=45),
            next_expiry_date=timezone.now() + datetime.timedelta(days=45) + datetime.timedelta(days=365*2),
        )
        report = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == 'processed'
        assert report[0][1] == tester_domain.name
        tester.refresh_from_db()
        assert tester.balance == 1000.0 - settings.ZENAIDA_DOMAIN_PRICE
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.domain_name == 'abcd.ai'
        assert new_notification.status == 'sent'
        assert new_notification.subject == 'domain_renewed'
        tester_orders = orders.list_orders(owner=tester)
        assert tester_orders[0].description == 'abcd.ai renew (automatically)'
        assert BackEndRenew.renewals.first().renew_order == tester_orders[0]
        report2 = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report2) == 0

    @pytest.mark.django_db
    def test_domain_auto_renew_disabled(self):
        tester = testsupport.prepare_tester_account(
            account_balance=1000.0,
            automatic_renewal_enabled=False,
        )
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            # domain was already synchronized from back-end with the new expiry date
            expiry_date=timezone.now() + datetime.timedelta(days=45) + datetime.timedelta(days=365*2),
            auto_renew_enabled=False,
        )
        zmaster.create_back_end_renew_notification(
            domain_name='abcd.ai',
            previous_expiry_date=timezone.now() + datetime.timedelta(days=45),
            next_expiry_date=timezone.now() + datetime.timedelta(days=45) + datetime.timedelta(days=365*2),
        )
        report = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report) == 0

    @pytest.mark.django_db
    @mock.patch('epp.rpc_client.cmd_domain_delete')
    def test_domain_auto_renew_disabled_domain_deleted(self, mock_cmd_domain_delete):
        mock_cmd_domain_delete.return_value = True
        tester = testsupport.prepare_tester_account(
            account_balance=1000.0,
            automatic_renewal_enabled=False,
        )
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            # domain was already synchronized from back-end with the new expiry date
            expiry_date=timezone.now() + datetime.timedelta(days=10) + datetime.timedelta(days=365*2),
            auto_renew_enabled=False,
        )
        zmaster.create_back_end_renew_notification(
            domain_name='abcd.ai',
            previous_expiry_date=timezone.now() + datetime.timedelta(days=10),
            next_expiry_date=timezone.now() + datetime.timedelta(days=10) + datetime.timedelta(days=365*2),
        )
        report = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == 'rejected'
        assert report[0][1] == tester_domain.name
        tester.refresh_from_db()
        assert tester.balance == 1000.0
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.domain_name == 'abcd.ai'
        assert new_notification.status == 'sent'
        assert new_notification.subject == 'domain_deleted'
        tester_orders = orders.list_orders(owner=tester)
        assert len(tester_orders) == 0
        mock_cmd_domain_delete.assert_called_once_with('abcd.ai')

    @pytest.mark.django_db
    @mock.patch('epp.rpc_client.cmd_domain_delete')
    def test_balance_not_enough_domain_deleted(self, mock_cmd_domain_delete):
        mock_cmd_domain_delete.return_value = True
        tester = testsupport.prepare_tester_account(account_balance=10.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            # domain was already synchronized from back-end with the new expiry date
            expiry_date=timezone.now() + datetime.timedelta(days=10) + datetime.timedelta(days=365*2),
            auto_renew_enabled=True,
        )
        zmaster.create_back_end_renew_notification(
            domain_name='abcd.ai',
            previous_expiry_date=timezone.now() + datetime.timedelta(days=10),
            next_expiry_date=timezone.now() + datetime.timedelta(days=10) + datetime.timedelta(days=365*2),
        )
        report = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == 'rejected'
        assert report[0][1] == tester_domain.name
        tester.refresh_from_db()
        assert tester.balance == 10.0
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.domain_name == 'abcd.ai'
        assert new_notification.status == 'sent'
        assert new_notification.subject == 'domain_deleted'
        tester_orders = orders.list_orders(owner=tester)
        assert len(tester_orders) == 0
        mock_cmd_domain_delete.assert_called_once_with('abcd.ai')

    @pytest.mark.django_db
    @mock.patch('epp.rpc_client.cmd_domain_delete')
    def test_balance_not_enough_domain_delete_failed(self, mock_cmd_domain_delete):
        mock_cmd_domain_delete.side_effect = rpc_error.EPPCommandFailed()
        tester = testsupport.prepare_tester_account(account_balance=10.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            # domain was already synchronized from back-end with the new expiry date
            expiry_date=timezone.now() + datetime.timedelta(days=10) + datetime.timedelta(days=365*2),
            auto_renew_enabled=True,
        )
        zmaster.create_back_end_renew_notification(
            domain_name='abcd.ai',
            previous_expiry_date=timezone.now() + datetime.timedelta(days=10),
            next_expiry_date=timezone.now() + datetime.timedelta(days=10) + datetime.timedelta(days=365*2),
        )
        report = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == 'delete_failed'
        assert report[0][1] == tester_domain.name
        report = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == 'delete_failed'
        assert report[0][1] == tester_domain.name
        assert len(mock_cmd_domain_delete.mock_calls) == 2

    @pytest.mark.django_db
    @mock.patch('epp.rpc_client.cmd_domain_delete')
    def test_balance_not_enough_domain_already_expired(self, mock_cmd_domain_delete):
        mock_cmd_domain_delete.return_value = True
        tester = testsupport.prepare_tester_account(account_balance=10.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            # domain was already synchronized from back-end with the new expiry date
            expiry_date=timezone.now() - datetime.timedelta(days=1) + datetime.timedelta(days=365*2),
            auto_renew_enabled=True,
        )
        zmaster.create_back_end_renew_notification(
            domain_name='abcd.ai',
            previous_expiry_date=timezone.now() - datetime.timedelta(days=1),
            next_expiry_date=timezone.now() - datetime.timedelta(days=1) + datetime.timedelta(days=365*2),
        )
        report = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == 'rejected'
        assert report[0][1] == tester_domain.name
        report2 = tasks.complete_back_end_auto_renewals(dry_run=False)
        assert len(report2) == 0


class TestAutoRenewExpiringDomains(TestCase):

    @pytest.mark.django_db
    @mock.patch('accounts.notifications.EmailMultiAlternatives.send')
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_order_created_executed_email_sent(self, mock_send, mock_domain_check_create_update_renew, mock_domain_synchronize_from_backend):
        mock_send.return_value = True
        mock_domain_check_create_update_renew.return_value = [True, ]
        mock_domain_synchronize_from_backend.return_value = [True, ]
        tester = testsupport.prepare_tester_account(account_balance=1000.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=True,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name
        tester.refresh_from_db()
        assert tester.balance == 1000.0 - settings.ZENAIDA_DOMAIN_PRICE
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.domain_name == 'abcd.ai'
        assert new_notification.status == 'sent'
        assert new_notification.subject == 'domain_renewed'
        tester_orders = orders.list_orders(owner=tester)
        assert tester_orders[0].description == 'abcd.ai renew (automatically)'

    @pytest.mark.django_db
    def test_auto_renew_started(self):
        tester = testsupport.prepare_tester_account(account_balance=200.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=True,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=True)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_auto_renew_for_expired_domain(self, mock_domain_check_create_update_renew, mock_domain_synchronize_from_backend):
        mock_domain_check_create_update_renew.return_value = [True, ]
        mock_domain_synchronize_from_backend.return_value = [True, ]
        tester = testsupport.prepare_tester_account(account_balance=200.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='suspended',
            expiry_date=timezone.now() - datetime.timedelta(days=1),  # expired yesterday
            auto_renew_enabled=True,
        )
        assert Notification.notifications.count() == 0
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name
        assert Notification.notifications.count() > 0

    @pytest.mark.django_db
    def test_pending_renew_order_already_exist(self):
        tester = testsupport.prepare_tester_account(account_balance=200.0)
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=True,
        )
        orders.order_single_item(
            owner=tester,
            item_type='domain_renew',
            item_price=100.0,
            item_name='abcd.ai',
            item_details={'some': 'details', },
        )
        report = tasks.auto_renew_expiring_domains(dry_run=True)
        assert len(report) == 0

    @pytest.mark.django_db
    def test_auto_renew_not_started_before_90_days(self):
        tester = testsupport.prepare_tester_account(account_balance=200.0)
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=95),  # will expire in 95 days
            auto_renew_enabled=True,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=True)
        assert len(report) == 0

    @pytest.mark.django_db
    def test_auto_renew_not_started_after_60(self):
        tester = testsupport.prepare_tester_account(account_balance=200.0)
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=55),  # will expire in 55 days
            auto_renew_enabled=True,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=True)
        assert len(report) == 0

    @pytest.mark.django_db
    def test_balance_not_enough(self):
        tester = testsupport.prepare_tester_account(account_balance=50.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=True,
        )
        assert Notification.notifications.count() == 0
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name
        assert report[0][1] == tester.email
        assert report[0][2].args[0] == 'not enough funds'
        assert Notification.notifications.count() > 0

    @pytest.mark.django_db
    def test_low_balance_notification_already_sent(self):
        tester = testsupport.prepare_tester_account(account_balance=50.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=True,
        )
        report1 = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report1) == 1
        assert report1[0][0] == tester_domain.name
        assert report1[0][1] == tester.email
        assert report1[0][2].args[0] == 'not enough funds'
        report2 = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report2) == 2
        assert report2[0][0] == tester_domain.name
        assert report2[0][1] == tester.email
        assert report2[0][2].args[0] == 'not enough funds'
        assert report2[1][0] == None
        assert report2[1][1] == tester.email
        assert report2[1][2].args[0] == 'notification already sent recently'

    @pytest.mark.django_db
    @mock.patch('billing.orders.execute_order')
    def test_execute_order_failed(self, mock_execute_order):
        mock_execute_order.return_value = 'failed'
        tester = testsupport.prepare_tester_account(account_balance=200.0)
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=True,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == tester_domain.name
        assert report[0][1] == tester.email
        assert report[0][2].args[0] == 'renew order status is failed'

    @pytest.mark.django_db
    def test_domain_auto_renew_disabled(self):
        tester = testsupport.prepare_tester_account(
            account_balance=200.0,
            automatic_renewal_enabled=False,
        )
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=False,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 0

    @pytest.mark.django_db
    def test_owner_profile_automatic_renewal_disabled(self):
        tester = testsupport.prepare_tester_account(
            account_balance=200.0,
            automatic_renewal_enabled=False,
        )
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=True,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1

    @pytest.mark.django_db
    def test_automatic_renewal_disabled_completely(self):
        tester = testsupport.prepare_tester_account(
            account_balance=200.0,
            automatic_renewal_enabled=False,
        )
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=timezone.now() + datetime.timedelta(days=89),  # will expire in 89 days
            auto_renew_enabled=False,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 0

    @pytest.mark.django_db
    @mock.patch('accounts.notifications.EmailMultiAlternatives.send')
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_owner_profile_email_notifications_disabled(self, mock_send, mock_domain_check_create_update_renew, mock_domain_synchronize_from_backend):
        mock_send.return_value = True
        mock_domain_check_create_update_renew.return_value = [True, ]
        mock_domain_synchronize_from_backend.return_value = [True, ]
        tester = testsupport.prepare_tester_account(account_balance=200.0, email_notifications_enabled=False)
        expiry_date = timezone.now() + datetime.timedelta(days=89)  # will expire in 89 days
        testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
            domain_status='active',
            expiry_date=expiry_date,
            auto_renew_enabled=True,
        )
        report = tasks.auto_renew_expiring_domains(dry_run=False)
        assert len(report) == 1
        assert report[0][0] == 'abcd.ai'
        assert report[0][1] == tester.email
        assert report[0][2] == expiry_date
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.status == 'skipped'
