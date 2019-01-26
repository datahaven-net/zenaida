import logging
import requests

from django import urls
from django import shortcuts
from django.core import exceptions
from django.conf import settings

from billing import payments


def start_payment(request, transaction_id):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')

    return shortcuts.render(request, 'billing/4csonline/start_payment.html', {
        'transaction_id': transaction_id,
    })


def process_payment(request):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    
    transaction_id = request.GET.get('transaction_id', '')
    payment_object = payments.by_transaction_id(transaction_id=transaction_id)

    if not payment_object:
        logging.critical('Payment not found, transaction_id=%s' % transaction_id)
        raise exceptions.SuspiciousOperation()

    if payment_object.owner != request.user:
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: payment owner is not matching to request')
        raise exceptions.SuspiciousOperation()

    if payment_object.finished_at:
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: payment transaction already finished')
        raise exceptions.SuspiciousOperation()

    return shortcuts.render(request, 'billing/4csonline/merchant_form.html', {
        'company_name': 'DATAHAVEN NET',
        'price': '{}.00'.format(int(payment_object.amount)),
        'merch_id': settings.BILLING_4CSONLINE_MERCHANT_ID,
        'merch_link': settings.BILLING_4CSONLINE_MERCHANT_LINK,
        'invoice': payment_object.transaction_id,
        'tran_id': payment_object.transaction_id,
        'url_approved': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
        'url_other': '{}{}'.format(settings.SITE_BASE_URL, urls.reverse('billing_4csonline_verify_payment')),
    })


def verify_payment(request):
    """
    """
    if request.GET.get('result') != 'pass' and request.GET.get('rc') == 'USERCAN' and request.GET.get('fc') == 'INCOMPLETE':
        if not payments.finish_payment(transaction_id=request.GET.get('tid'), status='cancelled'):
            logging.critical('Payment not found, transaction_id=%s' % request.GET.get('tid'))
            raise exceptions.SuspiciousOperation()
        return shortcuts.render(request, 'billing/4csonline/failed_payment.html', {
            'message': 'transaction was cancelled',
        })

    transaction_id = request.GET['invoice']
    payment_object = payments.by_transaction_id(transaction_id=transaction_id)
    if not payment_object:
        logging.critical('Payment not found, transaction_id=%s' % transaction_id)
        raise exceptions.SuspiciousOperation()

    if payment_object.finished_at:
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: payment transaction already finished')
        raise exceptions.SuspiciousOperation()

    if payment_object.amount != float(request.GET['amt'].replace(',', '')):
        logging.critical('Invalid request, payment processing will raise SuspiciousOperation: transaction amount not matching with existing record')
        raise exceptions.SuspiciousOperation()

    if not settings.BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION:
        if request.GET.get('result') != 'pass' or request.GET.get('rc') != 'OK' or request.GET.get('fc') != 'APPROVED':
            if request.GET.get('fc') == 'INCOMPLETE':
                message = 'transaction was cancelled'
                if not payments.finish_payment(transaction_id=transaction_id, status='cancelled'):
                    logging.critical('Payment not found, transaction_id=%s' % transaction_id)
                    raise exceptions.SuspiciousOperation()
            else:
                message = 'transaction was declined'
                if not payments.finish_payment(transaction_id=transaction_id, status='declined', merchant_reference=request.GET.get('ref')):
                    logging.critical('Payment not found, transaction_id=%s' % transaction_id)
                    raise exceptions.SuspiciousOperation()
            return shortcuts.render(request, 'billing/4csonline/failed_payment.html', {
                'message': message,
            })

    payments.update_payment(payment_object, status='paid', merchant_reference=request.GET.get('ref'))

    verified = requests.get('{}?m={}&t={}'.format(
        settings.BILLING_4CSONLINE_MERCHANT_VERIFY_LINK,
        settings.BILLING_4CSONLINE_MERCHANT_ID,
        payment_object.transaction_id,
    ))
    if not settings.BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION:
        if verified.text != 'YES':
            if not payments.finish_payment(transaction_id=transaction_id, status='unconfirmed'):
                logging.critical('Payment not found, transaction_id=%s' % transaction_id)
                raise exceptions.SuspiciousOperation()                
            message = 'transaction verification failed, please contact site administrator'
            logging.critical('Payment confirmation failed, transaction_id=%s' % payment_object.transaction_id)
            return shortcuts.render(request, 'billing/4csonline/failed_payment.html', {
                'message': message,
            })

    if not payments.finish_payment(transaction_id=transaction_id, status='processed'):
        logging.critical('Payment not found, transaction_id=%s' % transaction_id)
        raise exceptions.SuspiciousOperation()                
    
    return shortcuts.render(request, 'billing/4csonline/success_payment.html')
