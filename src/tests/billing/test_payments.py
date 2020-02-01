from django.test import TestCase

from billing import payments

from tests import testsupport


class TestOrders(TestCase):

    def test_latest_payment_found_started(self):
        tester_payment = testsupport.prepare_tester_payment()
        assert tester_payment == payments.latest_payment(owner=tester_payment.owner, status_in=['started', ])

    def test_latest_payment_not_found_processed(self):
        tester_payment = testsupport.prepare_tester_payment()
        assert payments.latest_payment(owner=tester_payment.owner, status_in=['processed', ]) is None
