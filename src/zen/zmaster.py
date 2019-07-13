import logging

from automats import contact_synchronizer
from automats import domains_checker
from automats import domain_synchronizer
from automats import domain_refresher
from automats import domain_resurrector


logger = logging.getLogger(__name__)


def contact_create_update(contact_object, raise_errors=False, log_events=True, log_transitions=True):
    """
    If `epp_id` field is empty, creates a new Contact or Registrant on back-end.
    Otherwise update existing object from `contact_object` info.
    Returns False if error happened, or raise Exception if `raise_errors` is True,
    """
    cs = contact_synchronizer.ContactSynchronizer(
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    cs.event('run', contact_object)
    outputs = list(cs.outputs)
    del cs
    logger.debug('contact_synchronizer(%r) finished with %d outputs', contact_object, len(outputs))

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if isinstance(outputs[-1], Exception):
            logger.error('contact_synchronizer(%r) failed with: %r', contact_object, outputs[-1])
        return False

    logger.info('contact_synchronizer(%r) OK', contact_object)
    return True


def domains_check(domain_names, verify_registrant=False, raise_errors=False, log_events=True, log_transitions=True):
    """
    Checks if those domains existing on Back-End.
    Returns dictionary object with check results.
    If `verify_registrant` is True process will also send domain_info() request to check epp_id on Back-End
    and compare with current registrant information stored in DB for every domain : epp_id must be in sync.
    Returns None if error happened, or raise Exception if `raise_errors` is True.
    """
    dc = domains_checker.DomainsChecker(
        skip_info=(not verify_registrant),
        verify_registrant=verify_registrant,
        stop_on_error=True,
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    dc.event('run', domain_names)
    outputs = list(dc.outputs)
    del dc
    logger.debug('domains_checker(%r) finished with %d outputs', domain_names, len(outputs))

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domains_checker(%r) failed with: %r', domain_names, outputs[-1])
        return None

    logger.info('domains_checker(%r) OK', domain_names)
    return outputs[-1]


def domain_check_create_update_renew(domain_object, sync_contacts=True, sync_nameservers=True, renew_years=None, save_to_db=True,
                                     raise_errors=False, log_events=True, log_transitions=True):
    """
    Check if domain exists first and then update it from `domain_object` info.
    If domain not exist create a new domain on back-end.
    If `renew_years` is positive integer it will also renew domain for that amount of years.
    If `renew_years=-1` it will use `domain_object.expiry_date` to decide how many days more needs to be added. 
    """
    ds = domain_synchronizer.DomainSynchronizer(
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    ds.event('run', domain_object,
        sync_contacts=sync_contacts,
        sync_nameservers=sync_nameservers,
        renew_years=renew_years,
        save_to_db=save_to_db,
    )
    outputs = list(ds.outputs)
    del ds
    logger.debug('domain_synchronizer(%r) finished with %d outputs', domain_object.name, len(outputs))

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if isinstance(outputs[-1], Exception):
            logger.error('domain_synchronizer(%r) failed with: %r', domain_object.name, outputs[-1])
        return False

    logger.info('domain_synchronizer(%r) OK', domain_object.name)
    return True


def domain_synchronize_from_backend(domain_name,
                                    refresh_contacts=False,
                                    change_owner_allowed=False,
                                    create_new_owner_allowed=False,
                                    soft_delete=False,
                                    raise_errors=False, log_events=True, log_transitions=True):
    """
    Requests domain info from backend and take required actions to update local DB
    to be fully in sync with  backend.
    If domain not exists in local DB it will be created.
    Returns False if error happened, or raise Exception if `raise_errors` is True,
    if all is okay returns domain object from local DB.
    """
    dr = domain_refresher.DomainRefresher(
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    dr.event('run',
        domain_name=domain_name,
        change_owner_allowed=change_owner_allowed,
        create_new_owner_allowed=create_new_owner_allowed,
        refresh_contacts=refresh_contacts,
        soft_delete=soft_delete,
    )
    outputs = list(dr.outputs)
    del dr
    logger.debug('domain_refresher(%r) finished with %d outputs', domain_name, len(outputs))
    return outputs


def domain_restore(domain_object, raise_errors=False, log_events=True, log_transitions=True, **kwargs):
    """
    Restores domain from "pendingDelete" state.
    """
    dr = domain_resurrector.DomainResurrector(
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    dr.event('run', domain_object=domain_object)
    outputs = list(dr.outputs)
    del dr

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if isinstance(outputs[-1], Exception):
            logger.error('domain_resurrector(%r) failed with: %r', domain_object.name, outputs[-1])
        return False

    logger.debug('domain_resurrector(%r) finished with %d outputs', domain_object.name, len(outputs))
    return True


def domain_set_auth_info(domain_object, auth_info=None, raise_errors=False, log_events=True, log_transitions=True, **kwargs):
    """
    Updates auth_info field for given domain on back-end side and also store it in the local DB. 
    """
    from automats import domain_auth_changer
    dac = domain_auth_changer.DomainAuthChanger(
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    dac.event('run', target_domain=domain_object, new_auth_info=auth_info)
    outputs = list(dac.outputs)
    del dac

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if isinstance(outputs[-1], Exception):
            logger.error('domain_auth_changer(%r) failed with: %r', domain_object.name, outputs[-1])
        return False

    logger.debug('domain_auth_changer(%r) finished with %d outputs', domain_object.name, len(outputs))
    return True
