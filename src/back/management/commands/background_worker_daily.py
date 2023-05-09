import logging

from django.core.management.base import BaseCommand

from logs.models import RequestLog

from zen import zdomains, zmaster

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Background process to execute regular tasks'

    def handle(self, *args, **options):
        # Sync real status of "to_be_deleted" domains from the back-end
        sync_to_be_deleted_domains_from_backend()
        # Need to clean up request logs
        cleanup_old_request_logs()


def sync_to_be_deleted_domains_from_backend():
    """
    Syncs domains with "to_be_deleted" status from the backend.
    """
    domains = zdomains.list_domains_by_status(status='to_be_deleted')
    for domain in domains:
        zmaster.domain_synchronize_from_backend(
            domain_name=domain.name,
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=False,
            create_new_owner_allowed=False,
            soft_delete=True,
            raise_errors=True,
            log_events=True,
            log_transitions=True,
        )
        domain.refresh_from_db()
        logger.info(f'{domain.name} status after backend sync: {domain.status}')


def cleanup_old_request_logs():
    deleted = RequestLog.erase_old_records(num_records=100000)
    logger.info(f'Cleanup request logs: {deleted[0]}')
