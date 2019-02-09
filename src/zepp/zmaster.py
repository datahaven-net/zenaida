import logging

from pika.exceptions import AMQPError

from zepp import zclient
from zepp import zerrors

from automats import domains_checker
from automats import domain_synchronizer


logger = logging.getLogger(__name__)


def domains_check(domain_names, verify_registrant=False, raise_errors=False):
    """
    Checks if those domains existing on Back-End.
    Returns dictionary object with check results.
    If `verify_registrant` is True process will also send domain_info() request to check epp_id on Back-End
    and compare with current registrant information stored in DB for every domain : epp_id must be in sync.
    Returns None if error happened, or raise Exception if `raise_errors` is False.
    """
    dc = domains_checker.DomainsChecker(
        skip_info=(not verify_registrant),
        verify_registrant=verify_registrant,
        stop_on_error=True,
        raise_errors=raise_errors,
    )
    dc.event('run', domain_names)
    result = dc.outputs[-1]
    if isinstance(result, Exception):
        if raise_errors:
            raise result
        return None
    return result


def domain_check_create_update_renew(domain_object, sync_contacts=True, sync_nameservers=True, renew_years=None, raise_errors=False, ):
    """
    """
    ds = domain_synchronizer.DomainSynchronizer(
        raise_errors=raise_errors,
    )
    ds.event('run', domain_object,
        sync_contacts=sync_contacts,
        sync_nameservers=sync_nameservers,
        renew_years=renew_years,
    )
    result = ds.outputs[-1]
    if isinstance(result, Exception):
        if raise_errors:
            raise result
        return None
    if result is not True:
        if raise_errors:
            raise Exception('Unexpected result in domain create flow')
        return None
    return result

