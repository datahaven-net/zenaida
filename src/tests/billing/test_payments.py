import pytest
from django.test import TestCase

from billing import payments

from tests import testsupport
from tests.testsupport import prepare_tester_account


class TestOrders(TestCase):

    def test_latest_payment_found_started(self):
        tester_payment = testsupport.prepare_tester_payment()
        assert tester_payment == payments.latest_payment(owner=tester_payment.owner, status_in=['started', ])

    def test_latest_payment_not_found_processed(self):
        tester_payment = testsupport.prepare_tester_payment()
        assert payments.latest_payment(owner=tester_payment.owner, status_in=['processed', ]) is None

    def test_list_all_payments_of_specific_method(self):
        testsupport.prepare_tester_payment()
        assert len(payments.list_all_payments_of_specific_method(method='pay_4csonline')) == 1
