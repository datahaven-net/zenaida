import logging

from django.utils import timezone

from back.models.domain import Domain

from zen import zmaster

logger = logging.getLogger(__name__)


def sync_expired_domains(dry_run=True):
    """
    When domain is expired COCCA back-end suppose to suspend it and send polling notification to Zenaida.
    But it is also possible that COCCA move it to another registrar - for example to put it on auction.
    In that case notification is not sent for some reason and Zenaida potentially can display wrong information to user.
    To workaround that we can keep track of all domains that are just expired few minutes ago and fetch the actual
    info from COCCA back-end for those. This way Zenaida will recognize the latest status of the domain and take
    required actions: remove domain from Zenaida DB.
    """
    moment_now = timezone.now()
    expired_active_domains = Domain.domains.filter(
        expiry_date__lte=moment_now,
        status='active',
    ).exclude(
        epp_id=None,
    )
    report = []
    for expired_domain in expired_active_domains:
        logger.info('domain %r is expired, going to synchronize from back-end', expired_domain)
        if dry_run:
            result = []
        else:
            result = zmaster.domain_synchronize_from_backend(
                domain_name=expired_domain.name,
                create_new_owner_allowed=False,
                domain_transferred_away=True,
                soft_delete=False,
            )
        report.append((expired_domain, result, ))
    return report
