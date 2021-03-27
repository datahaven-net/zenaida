import os
import string
import random

import pdfkit  # @UnresolvedImport

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import get_template

from billing.models.payment import Payment


def generate_transaction_id(size=16, chars=string.ascii_uppercase + string.digits):
    """
    Returns randomized text string.
    """
    return ''.join(random.choice(chars) for _ in range(size))


def latest_payment(owner, status_in=[]):
    """
    Returns latest payment started by given user or `None`.
    """
    try:
        query = Payment.payments.filter(owner=owner)
        if status_in:
            query = query.filter(status__in=status_in)
        return query.latest('started_at')
    except ObjectDoesNotExist:
        return None


def list_payments(owner, statuses=None):
    """
    List all payments started by given user.
    """
    if statuses is None:
        return list(Payment.payments.filter(owner=owner).all().order_by('-started_at'))
    return list(Payment.payments.filter(owner=owner, status__in=statuses).all().order_by('-started_at'))


def list_all_payments_of_specific_method(method):
    return Payment.payments.filter(method=method)


def iterate_payments(**kwargs):
    """
    Just an alias-method to iterate payments.
    """
    return Payment.payments.filter(**kwargs).all()


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


def finish_payment(transaction_id, status, merchant_reference=None, notes=None):
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
    if notes:
        payment_object.notes = notes
    payment_object.save()
    if old_status != new_status and new_status == 'processed':
        payment_object.owner.balance += payment_object.amount
        payment_object.owner.save()
    return payment_object


def build_invoice(payment_object):
    """
    Generates PDF document with invoice representing single payment record.
    """
    # Fill html template with the domain orders and user profile info
    html_template = get_template('billing/billing_invoice.html')
    rendered_html = html_template.render({
        'payment': payment_object,
        'user_profile': payment_object.owner.profile,
    })
    # Create pdf file from a html file
    pdfkit.from_string(rendered_html, '/tmp/out.pdf')
    with open("/tmp/out.pdf", "rb") as pdf_file:
        pdf_raw = pdf_file.read()
    os.remove("/tmp/out.pdf")
    return {
        'body': pdf_raw,
        'filename': 'invoice_{}.pdf'.format(payment_object.transaction_id),
    }
