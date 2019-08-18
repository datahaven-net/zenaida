import datetime

import mock
import pytest
from django.conf import settings
from django.test import TestCase

from accounts.management.commands import clean_inactive_activations_and_accounts
from accounts.models import Account
from accounts.models.activation import Activation
from back.models.domain import Domain
from back.models.zone import Zone
from billing.models.payment import Payment
from zen import zusers


class TestCleanInactiveActivationsAccounts(TestCase):
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
        clean_inactive_activations_and_accounts.cleanup()

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
        clean_inactive_activations_and_accounts.cleanup()

        assert len(Activation.objects.all()) == 0

        accounts = Account.objects.all()
        assert len(accounts) == 1
        assert accounts[0].email == "tester@zenaida.ai"

    @mock.patch('logging.Logger.warning')
    def test_delete_inactive_user(self, mock_logging):
        """
        Check if the account is removed as activation_code of the account is expired and the account is inactive
        and there is not any domain, balance or payment belongs to the account.
        """
        clean_inactive_activations_and_accounts.cleanup()

        assert len(Account.objects.all()) == 0
        assert len(Activation.objects.all()) == 0
        mock_logging.assert_called_once_with("Inactive account for this email address is removed: 'tester@zenaida.ai'")

    def test_do_not_delete_inactive_user_with_balance(self):
        """
        The account is inactive but there is a balance in user's account.
        Check if the expired activation is removed but the account is still there.
        """

        self.account.balance = 100.0
        self.account.save()
        clean_inactive_activations_and_accounts.cleanup()

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
        clean_inactive_activations_and_accounts.cleanup()

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
            amount=100,
            method="pay_btcpay",
            transaction_id="12345",
            started_at=datetime.datetime(2019, 3, 23),
            status="paid",
        )
        clean_inactive_activations_and_accounts.cleanup()

        assert len(Activation.objects.all()) == 0

        accounts = Account.objects.all()
        assert len(accounts) == 1
        assert accounts[0].email == "tester@zenaida.ai"

        payments = accounts[0].payments.all()
        assert len(payments) == 1
        assert payments[0].transaction_id == "12345"
