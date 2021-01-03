import logging
import datetime
import requests
import json

from django.conf import settings
from django.core.management.base import BaseCommand

from django.utils import timezone

from billing import payments

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Verifies known credit card payments against 4csonline system.'

    def add_arguments(self, parser):
        parser.add_argument('--past_days', type=int, default=60)
        parser.add_argument('--offset_minutes', type=int, default=60)
        parser.add_argument('--dry_run', action='store_true', dest='dry_run')

    def handle(self, past_days, offset_minutes, dry_run, *args, **options):
        moment_recently = timezone.now() - datetime.timedelta(minutes=offset_minutes)
        moment_2months_ago = timezone.now() - datetime.timedelta(days=past_days)
        total_count = 0
        cancelled_count = 0
        declined_count = 0
        modified_count = 0
        verified_count = 0
        fraud_count = 0
        failed_count = 0
        missed_count = 0
        suspicious_records = []

        for payment in payments.iterate_payments(
            method='pay_4csonline',
            started_at__gte=moment_2months_ago,
            started_at__lte=moment_recently,
        ):
            total_count += 1
            if payment.status == 'declined':
                declined_count += 1
                logger.debug('%r is declined', payment)
                continue

            try:
                verified = requests.get(f'{settings.ZENAIDA_BILLING_4CSONLINE_MERCHANT_VERIFY_LINK}?m='
                                        f'{settings.ZENAIDA_BILLING_4CSONLINE_MERCHANT_ID}&t={payment.transaction_id}')
            except Exception as exc:
                failed_count += 1
                logger.critical(f'payment confirmation failed {payment.transaction_id} : {exc}')
                continue

            if verified.text != 'YES':
                if payment.status in ['paid', 'processed', ]:
                    fraud_count += 1
                    suspicious_records.append(payment)
                    logger.critical('FRAUD! %r known as paid, but Bank result is %r', payment, verified.text)
                    continue

                if verified.text == 'NO':
                    if payment.status not in ['unconfirmed', 'started', ]:
                        suspicious_records.append(payment)
                        logger.warn('%r has unexpected status, but Bank status is %r', payment, verified.text)
                    if dry_run:
                        declined_count += 1
                        logger.debug('%r must be declined, Bank status is %r', payment, verified.text)
                        continue
                    if not payments.finish_payment(transaction_id=payment.transaction_id, status='declined'):
                        failed_count += 1
                        logger.critical(f'payment not found, transaction_id is {payment.transaction_id}')
                        continue
                    modified_count += 1
                    declined_count += 1
                    continue

                if verified.text == 'NOTFOUND':
                    if payment.status in ['started', ]:
                        if dry_run:
                            cancelled_count += 1
                            logger.debug('%r started, but not known to the Bank and must be cancelled', payment)
                            continue
                        if not payments.finish_payment(transaction_id=payment.transaction_id, status='cancelled'):
                            failed_count += 1
                            logger.critical(f'payment not found, transaction_id is {payment.transaction_id}')
                            continue
                        logger.info('%r was started while ago but not known to the Bank, cancelled', payment)
                        cancelled_count += 1
                        modified_count += 1
                        continue
                    logger.warn('%r is still pending, Bank status is %r', payment, verified.text)
                    continue

                failed_count += 1
                logger.critical('%r unexpected status from Bank: %r', payment, verified.text)
                continue

            if payment.status in ['unconfirmed', 'started', 'paid', ]:
                missed_count += 1
                verified_count += 1
                if dry_run:
                    logger.warn('%r must be accepted, Bank status is %r', payment, verified.text)
                    continue
                if not payments.finish_payment(transaction_id=payment.transaction_id, status='processed'):
                    failed_count += 1
                    logging.critical(f'payment not found, transaction_id is {payment.transaction_id}')
                    continue
                modified_count += 1
                logger.info('%r CONFIRMED and PROCESSED', payment)
                continue

            if payment.status not in ['processed', ]:
                suspicious_records.append(payment)
                failed_count += 1
                logger.critical('%r has unexpected status, Bank status is %r', payment, verified.text)
                continue

            verified_count += 1
            logger.debug('%r OK', payment)

        r = dict(
            total=total_count,
            missed=missed_count,
            cancelled=cancelled_count,
            declined=declined_count,
            modified=modified_count,
            verified=verified_count,
            fraud=fraud_count,
            failed=failed_count,
        )
        if failed_count + fraud_count + len(suspicious_records):
            self.stdout.write(self.style.ERROR(json.dumps(r, indent=4)))
        else:
            self.stdout.write(self.style.SUCCESS(json.dumps(r, indent=4)))
