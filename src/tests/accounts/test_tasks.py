import datetime

from django.utils import timezone

import mock
import pytest
from django.conf import settings
from django.test import TestCase

from tests import testsupport

from accounts.tasks import activations_cleanup, check_notify_domain_expiring
from accounts.models import Account
from accounts.models.activation import Activation
from accounts.models.notification import Notification
from accounts.notifications import process_notifications_queue
from back.models.domain import Domain
from back.models.zone import Zone
from billing.models.payment import Payment
from zen import zusers


class TestActivationsCleanup(TestCase):

    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account("tester@zenaida.ai", account_password="123", is_active=False)

        self.activation = Activation(code="12345", account=self.account)
        self.activation.save()
        self.activation.created_at = datetime.datetime.now() - datetime.timedelta(
            minutes=settings.ACTIVATION_CODE_EXPIRING_MINUTE + 1
        )
        self.activation.save()  # First save adds auto_now_add=True, that's why we should override it and save again.

    def test_do_not_delete_any_activation_code_or_account(self):
        """
        The activation code is not expired yet.
        Check if the activation and the account is still there.
        """
        self.activation.created_at = datetime.datetime.now()
        self.activation.save()
        activations_cleanup()

        assert len(Activation.objects.all()) == 1

        accounts = Account.objects.all()
        assert len(accounts) == 1
        assert accounts[0].email == "tester@zenaida.ai"

    def test_delete_expired_activation_code_of_active_account(self):
        """
        The account is active but activation code is still there after the expiring time.
        Check if the expired activation is removed but the account is still there.
        """
        self.account.is_active = True
        self.account.save()
        activations_cleanup()

        assert len(Activation.objects.all()) == 0

        accounts = Account.objects.all()
        assert len(accounts) == 1
        assert accounts[0].email == "tester@zenaida.ai"

    @mock.patch('logging.Logger.info')
    def test_delete_inactive_user(self, mock_logging):
        """
        Check if the account is removed as activation_code of the account is expired and the account is inactive
        and there is not any domain, balance or payment belongs to the account.
        """
        activations_cleanup()

        assert len(Account.objects.all()) == 0
        assert len(Activation.objects.all()) == 0
        mock_logging.assert_called_once()

    def test_do_not_delete_inactive_user_with_balance(self):
        """
        The account is inactive but there is a balance in user's account.
        Check if the expired activation is removed but the account is still there.
        """

        self.account.balance = 100.0
        self.account.save()
        activations_cleanup()

        assert len(Activation.objects.all()) == 0

        accounts = Account.objects.all()
        assert len(accounts) == 1
        assert accounts[0].email == "tester@zenaida.ai"
        assert accounts[0].balance == 100.0

    def test_do_not_delete_inactive_user_with_domain(self):
        """
        The account is inactive but there is a domain belongs to the user.
        Check if the expired activation is removed but the account is still there.
        """
        Domain.domains.create(
            owner=self.account,
            name="test.ai",
            zone=Zone.zones.create(name="ai"),
        )
        activations_cleanup()

        assert len(Activation.objects.all()) == 0

        accounts = Account.objects.all()
        assert len(accounts) == 1
        assert accounts[0].email == "tester@zenaida.ai"

        domains = accounts[0].domains.all()
        assert len(domains) == 1
        assert domains[0].name == "test.ai"

    def test_do_not_delete_inactive_user_with_payment(self):
        """
        The account is inactive but there is a domain belongs to the user.
        Check if the expired activation is removed but the account is still there.
        """
        Payment.payments.create(
            owner=self.account,
            amount=120,
            method="pay_btcpay",
            transaction_id="12345",
            started_at=datetime.datetime(2019, 3, 23),
            status="paid",
        )
        activations_cleanup()

        assert len(Activation.objects.all()) == 0

        accounts = Account.objects.all()
        assert len(accounts) == 1
        assert accounts[0].email == "tester@zenaida.ai"

        payments = accounts[0].payments.all()
        assert len(payments) == 1
        assert payments[0].transaction_id == "12345"


class TestCheckNotifyDomainExpiring(TestCase):

    @pytest.mark.django_db
    @mock.patch('accounts.notifications.EmailMultiAlternatives.send')
    def test_email_sent_and_executed(self, mock_send):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
        tester_domain.status = 'active'
        tester_domain.save()
        outgoing_emails = check_notify_domain_expiring(
            dry_run=False,
            min_days_before_expire=30,
            max_days_before_expire=60,
            subject='domain_expiring',
        )
        assert len(outgoing_emails) == 1
        assert outgoing_emails[0][0] == tester
        assert outgoing_emails[0][1] == tester_domain.name
        mock_send.return_value = True
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.subject == 'domain_expiring'
        assert new_notification.domain_name == 'abcd.ai'
        assert new_notification.status == 'sent'

    @pytest.mark.django_db
    def test_email_sent(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
        tester_domain.status = 'active'
        tester_domain.save()
        outgoing_emails = check_notify_domain_expiring(
            dry_run=True,
            min_days_before_expire=30,
            max_days_before_expire=60,
            subject='domain_expiring',
        )
        assert len(outgoing_emails) == 1
        assert outgoing_emails[0][0] == tester
        assert outgoing_emails[0][1] == tester_domain.name

    @pytest.mark.django_db
    def test_email_not_sent(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=61)  # expiry_date 61 days from now
        tester_domain.status = 'active'
        tester_domain.save()
        outgoing_emails = check_notify_domain_expiring(
            dry_run=True,
            min_days_before_expire=0,
            max_days_before_expire=30,
            subject='domain_expire_soon',
        )
        assert len(outgoing_emails) == 0

    @pytest.mark.django_db
    def test_alread_expired(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() - datetime.timedelta(days=10)  # already expired 10 days ago
        tester_domain.status = 'active'
        tester_domain.save()
        outgoing_emails = check_notify_domain_expiring(
            dry_run=True,
            min_days_before_expire=0,
            max_days_before_expire=30,
            subject='domain_expire_soon',
        )
        assert len(outgoing_emails) == 0

    @pytest.mark.django_db
    def test_not_active(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
        tester_domain.status = 'inactive'
        tester_domain.save()
        outgoing_emails = check_notify_domain_expiring(
            dry_run=True,
            min_days_before_expire=0,
            max_days_before_expire=30,
            subject='domain_expire_soon',
        )
        assert len(outgoing_emails) == 0

    @pytest.mark.django_db
    def test_blocked(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=15)  # expiry_date 15 days from now
        tester_domain.status = 'blocked'
        tester_domain.save()
        outgoing_emails = check_notify_domain_expiring(
            dry_run=True,
            min_days_before_expire=0,
            max_days_before_expire=30,
            subject='domain_expire_soon',
        )
        assert len(outgoing_emails) == 1
        assert outgoing_emails[0][0] == tester
        assert outgoing_emails[0][1] == tester_domain.name

    @pytest.mark.django_db
    def test_notifications_disabled(self):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester.profile.email_notifications_enabled = False
        tester.profile.save()
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=15)  # expiry_date 15 days from now
        tester_domain.status = 'active'
        tester_domain.save()
        outgoing_emails = check_notify_domain_expiring(
            dry_run=False,
            min_days_before_expire=0,
            max_days_before_expire=30,
            subject='domain_expire_soon',
        )
        assert len(outgoing_emails) == 0

    @pytest.mark.django_db
    @mock.patch('accounts.notifications.EmailMultiAlternatives.send')
    def test_no_duplicated_emails(self, mock_send):
        tester = testsupport.prepare_tester_account()
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='abcd.ai',
            tester=tester,
            domain_epp_id='aaa123',
        )
        tester_domain.expiry_date = timezone.now() + datetime.timedelta(days=45)  # expiry_date 45 days from now
        tester_domain.status = 'active'
        tester_domain.save()
        # first time
        outgoing_emails = check_notify_domain_expiring(
            dry_run=False,
            min_days_before_expire=30,
            max_days_before_expire=60,
            subject='domain_expiring',
        )
        assert len(outgoing_emails) == 1
        assert outgoing_emails[0][0] == tester
        assert outgoing_emails[0][1] == tester_domain.name
        mock_send.return_value = True
        process_notifications_queue(iterations=1, delay=0.1, iteration_delay=0.1)
        new_notification = Notification.notifications.first()
        assert new_notification.status == 'sent'
        # second time
        outgoing_emails_again = check_notify_domain_expiring(
            dry_run=False,
            min_days_before_expire=30,
            max_days_before_expire=60,
            subject='domain_expiring',
        )
        assert len(outgoing_emails_again) == 0
        # third time
        outgoing_emails_one_more = check_notify_domain_expiring(
            dry_run=False,
            min_days_before_expire=30,
            max_days_before_expire=60,
            subject='domain_expiring',
        )
        assert len(outgoing_emails_one_more) == 0
