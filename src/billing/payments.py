import string
import random

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from billing.models.payment import Payment


def generate_transaction_id(size=16, chars=string.ascii_uppercase + string.digits):
    """
    Returns randomized text string.
    """
    return ''.join(random.choice(chars) for _ in range(size))


def latest_payment(owner):
    """
    Returns latest payment started by given user or `None`.
    """
    try:
        return Payment.payments.filter(owner=owner).latest('started_at')
    except ObjectDoesNotExist:
        return None


def list_payments(owner, statuses=None):
    """
    List all payments started by given user.
    """
    if statuses is None:
        return list(Payment.payments.filter(owner=owner).all().order_by('-started_at'))
    return list(Payment.payments.filter(owner=owner, status__in=statuses).all().order_by('-started_at'))


def by_transaction_id(transaction_id):
    """
    Find payment by `transaction_id`.
    """
    return Payment.payments.filter(transaction_id=transaction_id).first()


def start_payment(owner, amount, payment_method):
    """
    Starts new payment for that user.
    """
    new_transaction_id = generate_transaction_id()
    while Payment.payments.filter(transaction_id=new_transaction_id).exists():
        new_transaction_id = generate_transaction_id()
    new_payment = Payment.payments.create(
        owner=owner,
        amount=amount,
        method=payment_method,
        transaction_id=new_transaction_id,
        started_at=timezone.now(),
    )
    return new_payment


def update_payment(payment_object, status=None, merchant_reference=None):
    """
    Updates existing payment object with new status.
    """
    if status is not None:
        payment_object.status = status
    if merchant_reference is not None:
        payment_object.merchant_reference = merchant_reference
    payment_object.save()
    return payment_object


def finish_payment(transaction_id, status, merchant_reference=None):
    """
    Finish already started payment.
    Also fill up user account balance if payment status is "processed".
    """
    payment_object = by_transaction_id(transaction_id=transaction_id)
    if not payment_object:
        return None
    old_status = payment_object.status
    new_status = status
    payment_object.status = status
    payment_object.finished_at = timezone.now()
    if merchant_reference is not None:
        payment_object.merchant_reference = merchant_reference
    payment_object.save()
    if old_status != new_status and new_status == 'processed':
        payment_object.owner.balance += payment_object.amount
        payment_object.owner.save()
    return payment_object
