import logging
import requests

from django import urls
from django import shortcuts
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import exceptions
from django.conf import settings
from django.views import View

from billing import payments
from billing import orders as billing_orders


class ProcessPaymentView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        transaction_id = kwargs.get('transaction_id', '')
        payment_object = payments.by_transaction_id(transaction_id=transaction_id)

        if not payment_object:
            logging.critical(f'payment not found, transaction_id is {transaction_id}')
            raise exceptions.SuspiciousOperation()

        if not payment_object.owner == request.user:
            logging.critical('invalid request, payment process raises SuspiciousOperation: '
                             'payment owner is not matching to request')
            raise exceptions.SuspiciousOperation()

        if payment_object.finished_at:
            logging.critical('invalid request, payment process raises SuspiciousOperation: '
                             'payment transaction is already finished')
            raise exceptions.SuspiciousOperation()

        payment_amount = round(payment_object.amount * (
            100.0 + settings.ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE) / 100.0, 2)

        return shortcuts.render(request, 'billing/4csonline/merchant_form.html', {
            'company_name': settings.ZENAIDA_BILLING_4CSONLINE_COMPANY_NAME,
            'price': '%.2f' % payment_amount,
            'merch_id': settings.ZENAIDA_BILLING_4CSONLINE_MERCHANT_ID,
            'merch_link': settings.ZENAIDA_BILLING_4CSONLINE_MERCHANT_LINK,
            'invoice': payment_object.transaction_id,
            'tran_id': payment_object.transaction_id,
            'url_approved': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
            'url_other': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
        })


class VerifyPaymentView(View):

    def _check_rc_usercan_is_incomplete(self, result, rc, fc, transaction_id):
        if result != 'pass' and rc == 'USERCAN' and fc == 'INCOMPLETE':
            self.message = 'Transaction was cancelled'
            if not payments.finish_payment(transaction_id=transaction_id, status='cancelled'):
                logging.critical(f'payment not found, transaction_id is {transaction_id}')
                raise exceptions.SuspiciousOperation()
            return True
        return False

    def _check_rc_ok_is_incomplete(self, result, rc, fc, transaction_id, reference):
        if result != 'pass' or rc != 'OK' or fc != 'APPROVED':
            if fc == 'INCOMPLETE':
                self.message = 'Transaction was cancelled'
                if not payments.finish_payment(transaction_id=transaction_id, status='cancelled'):
                    logging.critical(f'payment not found, transaction_id is {transaction_id}')
                    raise exceptions.SuspiciousOperation()
            else:
                self.message = 'Transaction was declined'
                if not payments.finish_payment(transaction_id=transaction_id, status='declined',
                                               merchant_reference=reference):
                    logging.critical(f'payment not found, transaction_id is {transaction_id}')
                    raise exceptions.SuspiciousOperation()
            return True
        return False

    @staticmethod
    def _check_payment(payment_obj, transaction_id, amount, curr):
        if not payment_obj:
            logging.critical(f'payment not found, transaction_id is {transaction_id}')
            raise exceptions.SuspiciousOperation()

        if payment_obj.finished_at:
            logging.critical('invalid request, payment process raises SuspiciousOperation: '
                             'payment transaction was already finished')
            raise exceptions.SuspiciousOperation()

        expected_payment_amount = round(payment_obj.amount * (
            100.0 + settings.ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE) / 100.0, 2)

        if str(curr).lower() != 'usd':
            if not payments.finish_payment(transaction_id=transaction_id, status='declined', notes='payment currency value is not USD'):
                logging.critical(f'payment not found, transaction_id is {transaction_id}')
                raise exceptions.SuspiciousOperation()
            logging.critical(f'payment is declined because currency value is not USD, transaction_id is {transaction_id}')
            raise exceptions.SuspiciousOperation()

        if float(amount) < expected_payment_amount:
            if not payments.finish_payment(transaction_id=transaction_id, status='declined', notes=f'payment amount {float(amount)} not matching expected {expected_payment_amount}'):
                logging.critical(f'payment not found, transaction_id is {transaction_id}')
                raise exceptions.SuspiciousOperation()
            logging.critical(f'payment is declined because of not matching amount value, transaction_id is {transaction_id}')
            raise exceptions.SuspiciousOperation()

        if float(amount) > expected_payment_amount:
            logging.critical('payment %r is overpaid: %r', payment_obj, amount)
        else:
            logging.info('payment %r is valid', payment_obj)

    def _is_payment_verified(self, transaction_id):
        try:
            verified = requests.get(f'{settings.ZENAIDA_BILLING_4CSONLINE_MERCHANT_VERIFY_LINK}?m='
                                    f'{settings.ZENAIDA_BILLING_4CSONLINE_MERCHANT_ID}&t={transaction_id}')
        except Exception as exc:
            self.message = 'Payment verification is pending, your balance will be updated within few minutes.'
            logging.critical(f'payment confirmation failed, transaction_id is {transaction_id} : {exc}')
            return 'pending'
        if verified.text != 'YES':
            if not payments.finish_payment(transaction_id=transaction_id, status='unconfirmed'):
                logging.critical(f'payment not found, transaction_id is {transaction_id}')
                raise exceptions.SuspiciousOperation()
            self.message = 'Transaction verification failed'
            logging.critical(f'payment confirmation failed, transaction_id is {transaction_id}')
            return 'failed'
        return 'verified'

    def get(self, request, *args, **kwargs):
        request_data = request.GET
        result = request_data.get('result')
        rc = request_data.get('rc')
        fc = request_data.get('fc')
        reference = request_data.get('ref')
        transaction_id = request_data.get('tid')
        amount = request_data.get('amt', '').replace(',', '')
        curr = request_data.get('curr', '')

        logging.info('verifying payment request: %r', request_data)

        if self._check_rc_usercan_is_incomplete(result, rc, fc, transaction_id):
            return shortcuts.render(request, 'billing/4csonline/failed_payment.html', {
                'message': self.message,  # TODO Use Django messages
            })

        payment_object = payments.by_transaction_id(transaction_id=transaction_id)
        self._check_payment(payment_object, transaction_id, amount, curr)

        if not settings.ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION:
            if self._check_rc_ok_is_incomplete(result, rc, fc, transaction_id, reference):
                return shortcuts.render(request, 'billing/4csonline/failed_payment.html', {
                    'message': self.message,
                })

        payments.update_payment(payment_object, status='paid', merchant_reference=reference)

        if not settings.ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION:
            result = self._is_payment_verified(transaction_id)
            if result == 'pending':
                return shortcuts.render(request, 'billing/4csonline/pending_payment.html', {
                    'message': self.message,
                })
            if result == 'failed':
                return shortcuts.render(request, 'billing/4csonline/failed_payment.html', {
                    'message': self.message,
                })

        if not payments.finish_payment(transaction_id=transaction_id, status='processed'):
            logging.critical(f'payment not found, transaction_id is {transaction_id}')  # TODO Use Django messages
            raise exceptions.SuspiciousOperation()

        redirect_url = '/billing/payments/'

        if not request.user.is_anonymous:
            started_orders = billing_orders.list_orders(
                owner=self.request.user,
                exclude_cancelled=True,
                include_statuses=['started']
            )
            if started_orders:
                messages.warning(self.request, 'You have an ongoing order. Please click the "Confirm" button '
                                               'to complete the order.')
                redirect_url = '/billing/order/' + str(started_orders[0].id)

        return shortcuts.render(request, 'billing/4csonline/success_payment.html', {
            'redirect_url': redirect_url,
            'amount': '$%s US' % amount,
        })
