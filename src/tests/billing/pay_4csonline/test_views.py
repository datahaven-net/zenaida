import datetime
import mock
import pytest

from django.test import TestCase, override_settings

from billing.models.order import Order
from billing.models.payment import Payment
from tests import testsupport
from zen import zusers


class BaseAuthTesterMixin(object):
    @pytest.mark.django_db
    def setUp(self):
        self.account = zusers.create_account('tester@zenaida.ai', account_password='123', is_active=True)
        self.client.login(email='tester@zenaida.ai', password='123')


class TestProcessPaymentView(BaseAuthTesterMixin, TestCase):
    """
    Tests successful scenario for processing the payment.
    """
    @override_settings(
        ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS=60,
        ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE=0.1
    )
    @pytest.mark.django_db
    def test_successful_process_payment(self):
        # Call payment endpoint to create payment first
        payment = self.client.post('/billing/pay/', data=dict(amount=2000, payment_method='pay_4csonline'))
        transaction_id = payment.context['transaction_id']
        response = self.client.get(f'/billing/4csonline/process/{transaction_id}/')
        assert response.status_code == 200
        assert response.context['tran_id'] == transaction_id
        assert response.context['price'] == '2002.00'

    @mock.patch('logging.critical')
    def test_payment_not_found(self, mock_logging_critical):
        """
        Tests process payment with wrong transaction id and check if SuspiciousOperation is logged.
        """
        self.client.post('/billing/pay/', data=dict(amount=100, payment_method='pay_4csonline'))
        response = self.client.get(f'/billing/4csonline/process/1234567890/')
        assert response.status_code == 400
        mock_logging_critical.assert_called_once_with(f'payment not found, transaction_id is 1234567890')

    @mock.patch('logging.critical')
    def test_payment_is_from_other_user(self, mock_logging_critical):
        """
        Tests process payment with transaction id which belongs to other user and
        check if SuspiciousOperation is logged.
        """
        account = zusers.create_account('other_user@zenaida.ai', account_password='123', is_active=True)
        Payment.payments.create(
            owner=account,
            amount=100,
            method='pay_4csonline',
            transaction_id='12345',
            started_at=datetime.datetime(2019, 3, 23),
            status='paid'
        )
        response = self.client.get(f'/billing/4csonline/process/12345/')
        assert response.status_code == 400
        mock_logging_critical.assert_called_once_with('invalid request, payment process raises SuspiciousOperation: '
                                                      'payment owner is not matching to request')

    @mock.patch('logging.critical')
    def test_payment_is_already_finished(self, mock_logging_critical):
        """
        Tests process payment with transaction id which was already finished and
        check if SuspiciousOperation is logged.
        """
        Payment.payments.create(
            owner=self.account,
            amount=100,
            method='pay_4csonline',
            transaction_id='12345',
            started_at=datetime.datetime(2019, 3, 23),
            finished_at=datetime.datetime(2019, 3, 24),
            status='paid'
        )
        response = self.client.get(f'/billing/4csonline/process/12345/')
        assert response.status_code == 400
        mock_logging_critical.assert_called_once_with('invalid request, payment process raises SuspiciousOperation: '
                                                      'payment transaction is already finished')


class TestVerifyPaymentView(BaseAuthTesterMixin, TestCase):

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE=0.1)
    @mock.patch('billing.payments.finish_payment')
    @mock.patch('billing.payments.update_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._is_payment_verified')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_ok_is_incomplete')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_success_payment_verify(
        self, mock_usercan_is_incomplete, mock_check_payment, mock_rc_ok_is_incomplete,
        mock_is_payment_verified, mock_update_payment, mock_finish_payment
    ):
        mock_usercan_is_incomplete.return_value = False
        mock_rc_ok_is_incomplete.return_value = False
        mock_is_payment_verified.return_value = True

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.10')
        assert response.status_code == 200
        assert response.context['redirect_url'] == '/billing/payments/'

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE=0.1)
    @mock.patch('billing.payments.finish_payment')
    @mock.patch('billing.payments.update_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._is_payment_verified')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_ok_is_incomplete')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_success_payment_verify_amount_with_comma(
        self, mock_usercan_is_incomplete, mock_rc_ok_is_incomplete,
        mock_is_payment_verified, mock_update_payment, mock_finish_payment
    ):
        payment_object = testsupport.prepare_tester_payment(tester=self.account, amount=1000)
        transaction_id = payment_object.transaction_id
        mock_usercan_is_incomplete.return_value = False
        mock_rc_ok_is_incomplete.return_value = False
        mock_is_payment_verified.return_value = True

        response = self.client.get(
            f'/billing/4csonline/verify/?result=miss&tid={transaction_id}&rc=OK&fc=APPROVED&app=&ref='
            f'1909569671030425&invoice={transaction_id}&tran_id={transaction_id}&err=&av=&amt=1,001.00')
        assert response.status_code == 200
        assert response.context['redirect_url'] == '/billing/payments/'

    @mock.patch('django.contrib.messages.warning')
    @mock.patch('billing.payments.finish_payment')
    @mock.patch('billing.payments.update_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._is_payment_verified')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_ok_is_incomplete')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_success_payment_redirects_to_started_order(
        self, mock_usercan_is_incomplete, mock_check_payment, mock_rc_ok_is_incomplete,
        mock_is_payment_verified, mock_update_payment, mock_finish_payment, mock_message_warning
    ):
        with mock.patch('billing.payments.by_transaction_id') as mock_payment_by_transaction_id:
            mock_payment_by_transaction_id.return_value = mock.MagicMock(
                status='started',
                amount=200.0,
                owner=self.account,
            )
        response = self.client.get('/billing/order/create/restore/test.ai/')
        assert response.status_code == 200
        orders = Order.orders.all()
        assert len(orders) == 1
        assert orders[0].status == 'started'

        mock_usercan_is_incomplete.return_value = False
        mock_rc_ok_is_incomplete.return_value = False
        mock_is_payment_verified.return_value = True

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')
        assert response.status_code == 200
        order_id = Order.orders.filter(owner=self.account)[0].id
        assert response.context['redirect_url'] == f'/billing/order/{order_id}'
        mock_message_warning.assert_called_once()


    @mock.patch('logging.critical')
    def test_check_rc_usercan_is_incomplete_suspicious_operation(self, mock_logging):
        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=USERCAN&fc=INCOMPLETE&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('payment not found, transaction_id is BPXKV4LXWQHA8RJH')

    @mock.patch('billing.payments.finish_payment')
    def test_check_rc_usercan_is_incomplete_transaction_cancelled(self, mock_finish_payment):
        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=USERCAN&fc=INCOMPLETE&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 200
        assert response.context['message'] == 'Transaction was cancelled'

    @mock.patch('logging.critical')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_check_payment_returns_payment_not_found(self, mock_usercan_is_incomplete, mock_logging):
        mock_usercan_is_incomplete.return_value = False

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('payment not found, transaction_id is BPXKV4LXWQHA8RJH')

    @mock.patch('logging.critical')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    @pytest.mark.django_db
    def test_check_payment_returns_payment_is_already_finished(self, mock_usercan_is_incomplete, mock_logging):
        mock_usercan_is_incomplete.return_value = False

        Payment.payments.create(
            owner=self.account,
            amount=100,
            method='pay_4csonline',
            transaction_id='BPXKV4LXWQHA8RJH',
            started_at=datetime.datetime(2019, 3, 23),
            finished_at=datetime.datetime(2019, 3, 24),
            status='paid'
        )

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('invalid request, payment process raises SuspiciousOperation: '
                                             'payment transaction is already finished')

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE=0.1)
    @mock.patch('logging.critical')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    @pytest.mark.django_db
    def test_check_payment_returns_payment_amount_not_matching(self, mock_usercan_is_incomplete, mock_logging):
        mock_usercan_is_incomplete.return_value = False

        Payment.payments.create(
            owner=self.account,
            amount=200,
            method='pay_4csonline',
            transaction_id='BPXKV4LXWQHA8RJH',
            started_at=datetime.datetime(2019, 3, 23),
            status='paid'
        )

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.10')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('invalid request, payment processing will raise SuspiciousOperation: '
                                             'transaction amount is not matching with existing record')

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION=False)
    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION=False)
    @mock.patch('logging.critical')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_check_rc_ok_is_incomplete_returns_suspicious_operation(
        self, mock_usercan_is_incomplete, mock_check_payment, mock_logging
    ):
        mock_usercan_is_incomplete.return_value = False

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=USERCAN&fc=INCOMPLETE&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('payment not found, transaction_id is BPXKV4LXWQHA8RJH')

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION=False)
    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION=False)
    @mock.patch('logging.critical')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_check_rc_ok_is_incomplete_returns_suspicious_operation_2(
        self, mock_usercan_is_incomplete, mock_check_payment, mock_logging
    ):
        mock_usercan_is_incomplete.return_value = False

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=USERCAN&fc=NOTAPPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('payment not found, transaction_id is BPXKV4LXWQHA8RJH')

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION=False)
    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION=False)
    @mock.patch('billing.payments.finish_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_rc_ok_is_incomplete_and_transaction_was_cancelled(self, mock_usercan_is_incomplete,
                                                               mock_check_payment, mock_finish_payment):
        mock_usercan_is_incomplete.return_value = False

        response = self.client.get(
            '/billing/4csonline/verify/?result=pass&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=INCOMPLETE&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 200
        assert response.context['message'] == 'Transaction was cancelled'

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION=False)
    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION=False)
    @mock.patch('billing.payments.finish_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_rc_ok_is_incomplete_and_transaction_was_declined(self, mock_usercan_is_incomplete,
                                                              mock_check_payment, mock_finish_payment):
        mock_usercan_is_incomplete.return_value = False

        response = self.client.get(
            '/billing/4csonline/verify/?result=pass&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=NOTAPPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 200
        assert response.context['message'] == 'Transaction was declined'

    @mock.patch('logging.critical')
    @mock.patch('requests.get')
    @mock.patch('billing.payments.update_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_ok_is_incomplete')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_is_payment_verified_returns_suspicious_operation(
        self, mock_usercan_is_incomplete, mock_check_payment, mock_rc_ok_is_incomplete,
        mock_payment_update, mock_get_response, mock_logging
    ):
        mock_usercan_is_incomplete.return_value = False
        mock_rc_ok_is_incomplete.return_value = False
        mock_get_response.return_value = mock.MagicMock(text='NO')

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('payment not found, transaction_id is BPXKV4LXWQHA8RJH')

    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION=False)
    @override_settings(ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION=False)
    @mock.patch('logging.critical')
    @mock.patch('requests.get')
    @mock.patch('billing.payments.finish_payment')
    @mock.patch('billing.payments.update_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_ok_is_incomplete')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_payment_verification_failed(
        self, mock_usercan_is_incomplete, mock_check_payment, mock_rc_ok_is_incomplete,
        mock_finish_payment, mock_payment_update, mock_get_response, mock_logging
    ):
        mock_usercan_is_incomplete.return_value = False
        mock_rc_ok_is_incomplete.return_value = False
        mock_get_response.return_value = mock.MagicMock(text='NO')

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 200
        assert response.context['message'] == 'Transaction verification failed, please contact site administrator'
        mock_logging.assert_called_once_with('payment confirmation failed, transaction_id is BPXKV4LXWQHA8RJH')

    @mock.patch('logging.critical')
    @mock.patch('billing.payments.update_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._is_payment_verified')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_ok_is_incomplete')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_payment')
    @mock.patch('billing.pay_4csonline.views.VerifyPaymentView._check_rc_usercan_is_incomplete')
    def test_finish_payment_fails(
        self, mock_usercan_is_incomplete, mock_check_payment, mock_rc_ok_is_incomplete,
        mock_is_payment_verified, mock_update_payment, mock_logging
    ):
        mock_usercan_is_incomplete.return_value = False
        mock_rc_ok_is_incomplete.return_value = False
        mock_is_payment_verified.return_value = True

        response = self.client.get(
            '/billing/4csonline/verify/?result=miss&tid=BPXKV4LXWQHA8RJH&rc=OK&fc=APPROVED&app=&ref='
            '1909569671030425&invoice=BPXKV4LXWQHA8RJH&tran_id=BPXKV4LXWQHA8RJH&err=&av=&amt=100.00')

        assert response.status_code == 400
        mock_logging.assert_called_once_with('payment not found, transaction_id is BPXKV4LXWQHA8RJH')
