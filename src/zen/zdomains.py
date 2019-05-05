import logging
import re
import datetime

from django.utils import timezone
from django.conf import settings
from django.core import exceptions

from back.models.registrar import Registrar

from zen import zzones
from zen import zusers

logger = logging.getLogger(__name__)


def is_valid(domain_name, idn=False):
    """
    Return `True` if domain name is valid.
    """
    regexp = '^[\w\-\.]*$'
    regexp_IP = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'
    if '.' not in domain_name:
        return False
    if re.match(regexp, domain_name) is None:
        return False
    if domain_name.startswith('-'):
        # -abcd.ai is not a valid name
        return False
    if not idn and domain_name.count('--'):
        # IDN domains are not allowed
        return False
    if len(domain_name) >= 4 and domain_name[2] == '.' and domain_name[1] == '-':
        # x-.com is not valid name
        return False
    if domain_name.count('-.'):
        # abcd-.com is not a valid name
        return False
    if domain_name.startswith('.'):
        # .abc.com is not a valid name
        return False
    if domain_name.endswith('.'):
        # abc.com. is not a valid name
        return False
    if domain_name.count('_.'):
        # xyz_.net is not a valid name
        return False
    if domain_name.startswith('_'):
        # _asdf.org is not a valid name
        return False
    if re.match(regexp_IP, domain_name.strip()) is not None:
        # must not look like IP address
        return False
    return True


def validate_domain_name(domain):
    """
    Raise `ValidationError()` if domain 
    """
    if is_valid(domain):
        return True
    raise exceptions.ValidationError('value "{}" is not a valid domain name'.format(domain))


def is_exist(domain_name='', epp_id=None):
    """
    Return `True` if domain exists, doing query in Domain table.
    """
    from back.models.domain import Domain
    if epp_id:
        return bool(Domain.domains.filter(epp_id=epp_id).first())
    return bool(Domain.domains.filter(name=domain_name).first())


def is_domain_available(domain_name):
    """
    Check if domain name exists, if it does not exist, then return True.

    If it exists, check if it's not created in last hour and if it doesn't have an epp_id
    OR if its expiry date is older than now and it doesn't have an epp_id, delete from internal DB and return True.
    """
    domain = domain_find(domain_name=domain_name)
    if not domain:
        return True
    if domain.epp_id:
        return False
    if domain.create_date.replace(tzinfo=None) + datetime.timedelta(hours=1) < datetime.datetime.utcnow():
        return True
    return False


def domain_find(domain_name='', epp_id=None):
    """
    Return `Domain` object if found in Domain table, else None.
    """
    from back.models.domain import Domain
    if epp_id:
        return Domain.domains.filter(epp_id=epp_id).first()
    return Domain.domains.filter(name=domain_name).first()


def domain_create(
        domain_name,
        owner,
        expiry_date=None,
        create_date=None,
        epp_id=None,
        auth_key='',
        registrar=None,
        registrant=None,
        contact_admin=None,
        contact_tech=None,
        contact_billing=None,
        nameservers=[],
        save=True,
    ):
    """
    Create new domain object in DB.
    """
    from back.models.domain import Domain
    if is_exist(domain_name=domain_name, epp_id=epp_id):
        raise ValueError('Domain already exists')
    if not create_date:
        create_date = timezone.now()
    if not contact_admin and not contact_tech and not contact_billing:
        raise ValueError('Must be set at least one of the domain contacts')
    if not registrant:
        registrant = [c for c in filter(None, [contact_admin, contact_tech, contact_billing, ])][0]
    if not registrar or not isinstance(registrar, Registrar):
        registrar = Registrar.registrars.get_or_create(
            epp_id=(registrar or settings.ZENAIDA_REGISTRAR_ID),
        )[0]
    zone = zzones.make('.'.join(domain_name.split('.')[1:]))
    new_domain = Domain(
        name=domain_name,
        owner=owner,
        expiry_date=expiry_date,
        create_date=create_date,
        epp_id=epp_id,
        auth_key=auth_key,
        registrar=registrar,
        zone=zone,
    )
    if registrant:
        new_domain.registrant = registrant
    if contact_admin:
        new_domain.contact_admin = contact_admin
    if contact_tech:
        new_domain.contact_tech = contact_tech
    if contact_billing:
        new_domain.contact_billing = contact_billing
    host_position = 0
    for nameserver in nameservers:
        if nameserver:
            new_domain.set_nameserver(host_position, nameserver)
        host_position += 1
    if save:
        new_domain.save()
    logger.debug('domain created: %r', new_domain)
    return new_domain


def domain_update(domain_name, **kwargs):
    """
    Simply updates domain info with new values.
    """
    from back.models.domain import Domain
    Domain.domains.filter(name=domain_name).update(**kwargs)
    return None


def domain_delete(domain_id=None, domain_name=None):
    """
    Removes domain with given primary ID from DB.
    """
    from back.models.domain import Domain
    if domain_name is not None:
        return Domain.domains.filter(name=domain_name).delete()
    return Domain.domains.filter(id=domain_id).delete()


def domain_change_registrant(domain_object, new_registrant_object, save=True):
    """
    Change registrant of the domain.
    Need to keep in mind that each registrant must have same owner as a domain he controls.
    """
    new_owner = new_registrant_object.owner
    current_registrant = domain_object.registrant
    domain_object.registrant = new_registrant_object
    domain_object.owner = new_owner
    if save:
        domain_object.save()
    logger.debug('domain %s registrant changed: %r -> %r', domain_object.name, current_registrant, new_registrant_object)
    return domain_object


def domain_change_owner(domain_object, new_owner, save=True):
    """
    Change owner of the domain.
    Need to keep in mind that each registrant must have same owner as a domain he controls.
    """
    current_owner = domain_object.owner
    count = 0
    for registrant in domain_object.registrants:
        # change owners all of my known registrant contacts (I can have multiple ...)
        registrant.owner = new_owner
        if save:
            registrant.owner.save()
        count += 1
    domain_object.owner = new_owner
    if save:
        domain_object.save()
    logger.debug('domain %s owner changed (and all %d registrants): %r -> %r', domain_object.name, count, current_owner, new_owner)
    return domain_object


def domain_join_contact(domain_object, role, new_contact_object):
    """
    Add/Change single contact with given role of that domain.
    This will only create a new relation, contact object must already exist.
    """
    current_contact = domain_object.get_contact(role)
    domain_object.set_contact(role, new_contact_object)
    domain_object.save()
    logger.debug('domain %s contact "%s" modified : %r -> %r', domain_object.name, role, current_contact, new_contact_object)
    return domain_object


def domain_detach_contact(domain_object, role):
    """
    Remove given contact with given role from that domain.
    This will only remove existing relation, contact object is not removed.
    """
    current_contact = domain_object.get_contact(role)
    domain_object.set_contact(role, None)
    domain_object.save()
    logger.debug('domain %s contact "%s" disconnected, previous was : %r', domain_object.name, role, current_contact)
    return domain_object


def get_last_registered_domain(registrant_email):
    """
    If user has any domain, return latest registered domain of the user by email else empty list.
    """
    existing_account = zusers.find_account(registrant_email)
    if existing_account:
        domains = existing_account.domains.all()
        if domains:
            return domains.order_by('-create_date')[0]
    return []


def list_domains(registrant_email):
    """
    List all domains for given user identified by email where he have registrant role assigned.
    """
    existing_account = zusers.find_account(registrant_email)
    if not existing_account:
        return []
    return list(existing_account.domains.all())

#------------------------------------------------------------------------------

def check_nameservers_changed(domain_object, domain_info_response=None):
    """
    Compares known domain nameservers received from EPP response and currently stored in db,
    return True if some change found: add or remove nameserver.
    TODO: check can't we just compare two lists... ?
    """
    try:
        current_servers = domain_info_response['epp']['response']['resData']['infData']['ns']['hostObj']
    except:
        current_servers = []
    if not isinstance(current_servers, list):
        current_servers = [current_servers, ]
    for old_server in current_servers:
        if old_server and old_server not in domain_object.list_nameservers():
            return True
    for new_server in domain_object.list_nameservers():
        if new_server and new_server not in current_servers:
            return True
    return False


def compare_nameservers(domain_object, domain_info_response=None):
    """
    Based on known EPP domain info and local info from database identify which name servers needs to be added or removed.
    """
    remove_nameservers = []
    add_nameservers = []
    try:
        current_nameservers = domain_info_response['epp']['response']['resData']['infData']['ns']['hostObj']
    except:
        current_nameservers = []
    if not isinstance(current_nameservers, list):
        current_nameservers = [current_nameservers, ]
    new_nameservers = domain_object.list_nameservers()
    for old_server in current_nameservers:
        if old_server and old_server not in new_nameservers:
            remove_nameservers.append(old_server)
    for new_server in new_nameservers:
        if new_server and new_server not in current_nameservers:
            add_nameservers.append(new_server)
    return add_nameservers, remove_nameservers


def update_nameservers(domain_object, hosts=[], domain_info_response=None):
    """
    Create or update nameservers hosts for given domain.
    Value `hosts` is a list of 4 items.
    None or empty string in the list means nameserver not set at given position.
    """
    if domain_info_response:
        try:
            current_nameservers = domain_info_response['epp']['response']['resData']['infData']['ns']['hostObj']
        except:
            current_nameservers = []
        if not isinstance(current_nameservers, list):
            current_nameservers = [current_nameservers, ]
        hosts = current_nameservers
    existing_nameservers = domain_object.list_nameservers()
    domain_modified = False
    for i in range(len(hosts)):
        if hosts[i]:
            if existing_nameservers[i] != hosts[i]:
                logger.debug('nameserver host at position %d to be changed for %s : %s -> %s',
                             i, domain_object, existing_nameservers[i], hosts[i])
                domain_object.set_nameserver(i, hosts[i])
                domain_modified = True
        else:
            logger.debug('nameserver host at position %d to be erased for %s', i, domain_object)
            domain_object.clear_nameserver(i)
            domain_modified = True
    if domain_modified:
        domain_object.save()
    return domain_modified

#------------------------------------------------------------------------------

def compare_contacts(domain_object, domain_info_response=None, target_contacts=None):
    """
    Based on known EPP domain info and local info from database identify which contacts needs to be added or removed.
    Also checks if registrant needs to be changed.
    """
    add_contacts = []
    remove_contacts = []
    change_registrant = None
    if not target_contacts:
        target_contacts = domain_object.list_contacts()
    #--- contacts
    new_contacts = []
    try:
        current_contacts = domain_info_response['epp']['response']['resData']['infData']['contact']
    except:
        current_contacts = []
    if not isinstance(current_contacts, list):
        current_contacts = [current_contacts, ]
    current_contacts = [{
        'type': i['@type'],
        'id': i['#text'],
    } for i in current_contacts]
    for role, contact_object in target_contacts:
        if role == 'registrant':
            continue
        if contact_object:
            if contact_object.epp_id:
                new_contacts.append({'type': role, 'id': contact_object.epp_id, })
    current_contacts_ids = [old_contact['id'] for old_contact in current_contacts]
    for new_cont in new_contacts:
        if new_cont['id'] not in current_contacts_ids:
            add_contacts.append(new_cont)
    new_contacts_ids = [new_cont['id'] for new_cont in new_contacts]
    for old_cont in current_contacts:
        if old_cont['id'] not in new_contacts_ids:
            remove_contacts.append(old_cont)
    #--- registrant
    current_registrant = None
    try:
        current_registrant = domain_info_response['epp']['response']['resData']['infData']['registrant']
    except:
        pass
    if domain_object.registrant and current_registrant and current_registrant != domain_object.registrant.epp_id:
        change_registrant = domain_object.registrant.epp_id
    return add_contacts, remove_contacts, change_registrant

#------------------------------------------------------------------------------

def response_to_datetime(field_name, domain_info_response):
    return datetime.datetime.strptime(
        domain_info_response['epp']['response']['resData']['infData'][field_name],
        '%Y-%m-%dT%H:%M:%S.%fZ',
    )

#------------------------------------------------------------------------------

def domain_update_statuses(domain_object, domain_info_response, save=True):
    """
    Update given Domain object from epp domain_info response. 
    """
    current_domain_statuses = domain_object.epp_statuses or {}
    new_domain_statuses = {}
    try:
        epp_statuses = domain_info_response['epp']['response']['resData']['infData']['status']
    except:
        logger.exception('Failed to read domain statuses from domain_info response')
        return False
    if not isinstance(epp_statuses, list):
        epp_statuses = [epp_statuses, ]
    for st in epp_statuses:
        new_domain_statuses[str(st['@s'])] = st['#text']
    modified = (sorted(current_domain_statuses.keys()) != sorted(new_domain_statuses.keys()))
    domain_object.epp_statuses = new_domain_statuses
    if 'ok' in new_domain_statuses:
        domain_object.status = 'active'
    else:
        domain_object.status = 'inactive'
        if 'pendingDelete' in new_domain_statuses:
            domain_object.status = 'to_be_deleted'
    if save:
        domain_object.save()
    if modified:
        logger.info('domain %r statuses modified:  %r -> %r', domain_object, current_domain_statuses, new_domain_statuses)
    return True
