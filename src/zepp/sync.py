import logging

from zepp import zmaster

logger = logging.getLogger(__name__)


def domain_sync(domain_name, raise_errors=False):
    """
    Request actual info from EPP Registry about specified domain and populate data in local DB.
    """
    domain_exists = zmaster.domain_check(domain_name, raise_errors=raise_errors)
    if domain_exists is None:
        return None