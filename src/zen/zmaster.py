import logging

from automats import contact_synchronizer
from automats import domains_checker
from automats import domain_synchronizer
from automats import domain_refresher
from automats import domain_resurrector
from automats import domain_contacts_synchronizer

from epp import rpc_error

from zen import zerrors

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
    logger.info('contact_synchronizer(%r) finished with %d outputs', contact_object, len(outputs))

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if outputs and isinstance(outputs[-1], Exception):
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
        skip_check=False,
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
    logger.info('domains_checker(%r) finished with %d outputs', domain_names, len(outputs))

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domains_checker(%r) failed with: %r', domain_names, outputs[-1])
        if outputs and isinstance(outputs[-1], zerrors.NonSupportedZone):
            return 'non-supported-zone'
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
        accept_code_2304=True,
    )
    ds.event('run', domain_object,
        sync_contacts=sync_contacts,
        sync_nameservers=sync_nameservers,
        renew_years=renew_years,
        save_to_db=save_to_db,
    )
    outputs = list(ds.outputs)
    del ds
    logger.info('domain_synchronizer(%r) finished with %d outputs', domain_object.name, len(outputs))

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domain_synchronizer(%r) failed with: %r', domain_object.name, outputs[-1])
        return False

    logger.info('domain_synchronizer(%r) OK', domain_object.name)
    return True


def domain_synchronize_from_backend(domain_name,
                                    refresh_contacts=False,
                                    rewrite_contacts=None,
                                    change_owner_allowed=False,
                                    create_new_owner_allowed=False,
                                    soft_delete=True,
                                    domain_transferred_away=False,
                                    raise_errors=False, log_events=True, log_transitions=True):
    """
    Requests domain info from back-end and take required actions to update local DB
    to be in sync with COCCA back-end, but with some limitations.
    If domain not exists in local DB it will be created.
    If domain not exist on COCCA anymore, or owned by another registrar it will be removed from local DB,
    but only if `soft_delete=False`. Otherwise marked as INACTIVE.
    Skip any actions with domain contacts if `refresh_contacts=False`.
    If `rewrite_contacts=True` will actually first write current contact IDs is from DB to COCCA and
    then do the full contacts details synchronization, thus actually rewrite contacts on back-end.
    """
    dr = domain_refresher.DomainRefresher(
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    outputs = []
    try:
        dr.event('run',
            domain_name=domain_name,
            change_owner_allowed=change_owner_allowed,
            create_new_owner_allowed=create_new_owner_allowed,
            refresh_contacts=refresh_contacts,
            rewrite_contacts=rewrite_contacts,
            soft_delete=soft_delete,
            domain_transferred_away=domain_transferred_away,
        )
        outputs = list(dr.outputs)
    except rpc_error.EPPError as exc:
        dr.destroy()
        outputs = [exc, ]
    del dr
    logger.info('domain_refresher(%r) finished with %d outputs', domain_name, len(outputs))
    return outputs


def domain_synchronize_contacts(domain_object,
                                skip_roles=[], skip_contact_details=False,
                                merge_duplicated_contacts=False,
                                rewrite_registrant=False, new_registrant=None,
                                raise_errors=False, log_events=True, log_transitions=True):
    """
    Write domain contacts to the back-end including contacts details info.
    Must pass `rewrite_registrant=True` if need to write registrant info also.
    Also de-duplicates contacts if `merge_duplicated_contacts=True`.
    """
    if rewrite_registrant:
        from zen import zcontacts
        new_registrant = new_registrant or zcontacts.get_oldest_registrant(domain_object.owner)
    dcs = domain_contacts_synchronizer.DomainContactsSynchronizer(
        update_domain=True,
        skip_roles=skip_roles,
        skip_contact_details=skip_contact_details,
        merge_duplicated_contacts=merge_duplicated_contacts,
        new_registrant=new_registrant,
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    dcs.event('run', target_domain=domain_object, )
    outputs = list(dcs.outputs)
    del dcs

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domain_synchronize_contacts(%r) failed with: %r', domain_object.name, outputs[-1])
        else:
            logger.error('domain_synchronize_contacts(%r) unexpectedly failed with: %r', domain_object.name, outputs)
        return outputs or []

    logger.info('domain_synchronize_contacts(%r) finished with %d outputs', domain_object.name, len(outputs))
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
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domain_resurrector(%r) failed with: %r', domain_object.name, outputs[-1])
        else:
            logger.error('domain_resurrector(%r) unexpectedly failed with: %r', domain_object.name, outputs)
        return False

    logger.info('domain_resurrector(%r) finished with %d outputs', domain_object.name, len(outputs))
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
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domain_auth_changer(%r) failed with: %r', domain_object.name, outputs[-1])
        else:
            logger.error('domain_auth_changer(%r) unexpectedly failed with: %r', domain_object.name, outputs)
        return False

    logger.info('domain_auth_changer(%r) finished with %d outputs', domain_object.name, len(outputs))
    return True


def domain_transfer_request(domain, auth_info, skip_info=False, raise_errors=False, log_events=True, log_transitions=True):
    """
    Sending domain transfer request to the back-end. As soon as back-end process the request and accept transfer
    new event message suppose to be received via polling script and new domain object will be created in Zenaida DB.
    This method only initiate the request. You must provide "authentication code" for that domain
    to be able to transfer it to Zenaida.  
    """
    from automats import domain_transfer_requestor
    dtr = domain_transfer_requestor.DomainTransferRequestor(
        skip_info=skip_info,
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    dtr.event('run', target_domain_name=domain, auth_info=auth_info)
    outputs = list(dtr.outputs)
    del dtr

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domain_transfer_request(%r) failed with: %r', domain, outputs[-1])
        else:
            logger.error('domain_transfer_request(%r) unexpectedly failed with: %r', domain, outputs)
        return False

    logger.info('domain_transfer_request(%r) finished with %d outputs', domain, len(outputs))
    return True


def domain_read_info(domain, auth_info=None, raise_errors=False, log_events=True, log_transitions=True):
    """
    Request from back-end and returns actual info about the domain.
    """
    dc = domains_checker.DomainsChecker(
        skip_check=True,
        skip_info=False,
        verify_registrant=False,
        stop_on_error=True,
        log_events=log_events,
        log_transitions=log_transitions,
        raise_errors=raise_errors,
    )
    dc.event('run', [domain, ], auth_info=auth_info, )
    outputs = list(dc.outputs)
    del dc
    logger.info('domains_checker(%r) finished with %d outputs', domain, len(outputs))

    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        if outputs and isinstance(outputs[-1], Exception):
            logger.error('domains_checker(%r) failed with: %r', domain, outputs[-1])
        else:
            logger.error('domains_checker(%r) unexpectedly failed with: %r', domain, outputs)
        if raise_errors:
            if not outputs or not outputs[-1]:
                raise Exception('empty response')
            elif outputs and isinstance(outputs[-1], Exception):
                raise outputs[-1]
            else:
                raise Exception(outputs)
        return None

    if not outputs[-1].get(domain):
        logger.error('domains_checker(%r) failed because domain not exist', domain)
        if raise_errors:
            raise zerrors.DomainNotExist()
        return None

    if len(outputs) < 2:
        logger.error('domains_checker(%r) failed with: %r', domain, outputs[-1])
        if raise_errors:
            raise zerrors.UnexpectedEPPResponse(outputs)
        return None

    logger.info('domains_checker(%r) OK', domain)
    return outputs[-2]
