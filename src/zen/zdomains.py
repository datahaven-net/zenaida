import logging
import re
import datetime
import random
import string

from django.db.models import Q
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
    if domain_name.count('..'):
        # abcd..com is not a valid name
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
    Will raise `ValidationError` exception if domain name is not valid.
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
    if not domain.create_date:
        return True
    if domain.create_date.replace(tzinfo=None) + datetime.timedelta(hours=1) < datetime.datetime.utcnow():
        return True
    return False


def domain_find(domain_name='', epp_id=None, domain_id=None):
    """
    Return `Domain` object if found in Domain table, else None.
    """
    from back.models.domain import Domain
    if domain_id:
        return Domain.domains.filter(id=domain_id).first()
    if epp_id:
        return Domain.domains.filter(epp_id=epp_id).first()
    return Domain.domains.filter(name=domain_name.strip().lower()).first()


def domain_create(
        domain_name,
        owner,
        expiry_date=None,
        create_date=None,
        epp_id=None,
        status=None,
        epp_statuses=None,
        auth_key='',
        registrar=None,
        registrant=None,
        contact_admin=None,
        contact_tech=None,
        contact_billing=None,
        nameservers=[],
        auto_renew_enabled=None,
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
    if not registrant:
        input_contacts = [c for c in filter(None, [contact_admin, contact_tech, contact_billing, ])]
        if input_contacts:
            registrant = input_contacts[0]
    if not registrant:
        raise ValueError('Registrant info is required, also no contact info was found')
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
    if status:
        new_domain.status = status
    if epp_statuses is not None:
        new_domain.epp_statuses = epp_statuses
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
    if auto_renew_enabled is not None:
        new_domain.auto_renew_enabled = auto_renew_enabled
    else:
        new_domain.auto_renew_enabled = owner.profile.automatic_renewal_enabled
    if save:
        new_domain.save()
    logger.info('domain created: %r', new_domain)
    return new_domain


def domain_update(domain_name, **kwargs):
    """
    Simply updates domain info with new values.
    """
    from back.models.domain import Domain
    Domain.domains.filter(name=domain_name).update(**kwargs)
    return None


def domain_unregister(domain_id=None, domain_name=None):
    """
    Marks domain as being not registered on the back-end.
    Clean up its epp_id field and few other fields.
    Domain will have no connection with back-end anymore. 
    """
    domain_object = domain_find(domain_id=domain_id, domain_name=domain_name)
    if not domain_object:
        return False
    domain_object.status = 'inactive'
    domain_object.expiry_date = None
    domain_object.create_date = None
    domain_object.epp_id = None
    domain_object.epp_statuses = None
    domain_object.auth_key = ''
    domain_object.save()
    logger.info('domain %r unregistered', domain_object)
    return True


def domain_delete(domain_id=None, domain_name=None):
    """
    Removes domain with given primary ID from DB.
    """
    from back.models.domain import Domain
    if domain_name is not None:
        logger.info('domain %r will be removed', domain_name)
        return Domain.domains.filter(name=domain_name).delete()
    logger.info('domain domain_id=%r will be removed', domain_id)
    return Domain.domains.filter(id=domain_id).delete()


def domain_change_registrant(domain_object, new_registrant_object, save=True):
    """
    Change registrant of the domain.
    Need to keep in mind that each registrant must have same owner as a domain he controls.
    """
    new_owner = new_registrant_object.owner
    current_owner = domain_object.owner
    current_registrant = domain_object.registrant
    domain_object.registrant = new_registrant_object
    domain_object.owner = new_owner
    if save:
        domain_object.save()
    logger.info('domain %r registrant changed: %r -> %r', domain_object.name, current_registrant, new_registrant_object)
    if current_owner != new_owner:
        logger.info('domain %r owner changed after registrant update: %r -> %r', domain_object.name, current_owner, new_owner)
    return domain_object


def domain_change_owner(domain_object, new_owner, also_registrants=True, save=True):
    """
    Change owner of the domain.
    Need to keep in mind that each registrant must have same owner as a domain he controls.
    """
    current_owner = domain_object.owner
    count = 0
    if also_registrants:
        for registrant in domain_object.owner.registrants.all():
            # change owners all of my known registrant contacts (I can have multiple ...)
            registrant.owner = new_owner
            if save:
                registrant.save()
            count += 1
    domain_object.owner = new_owner
    if save:
        domain_object.save()
    logger.info('domain %r owner changed (also for %d registrants): %r -> %r', domain_object.name, count, current_owner, new_owner)
    return domain_object


def domain_join_contact(domain_object, role, new_contact_object):
    """
    Add/Change single contact with given role of that domain.
    This will only create a new relation, contact object must already exist.
    """
    current_contact = domain_object.get_contact(role)
    if current_contact == new_contact_object:
        logger.info('domain %s contact "%s" was not modified', domain_object.name, role)
        return domain_object
    domain_object.set_contact(role, new_contact_object)
    domain_object.save()
    logger.info('domain %r contact role %r modified : %r -> %r', domain_object.name, role, current_contact, new_contact_object)
    return domain_object


def domain_detach_contact(domain_object, role):
    """
    Remove given contact with given role from that domain.
    This will only remove existing relation, contact object is not removed.
    """
    current_contact = domain_object.get_contact(role)
    domain_object.set_contact(role, None)
    domain_object.save()
    logger.info('domain %r contact role %r disconnected, previous was : %r', domain_object.name, role, current_contact)
    return domain_object


def domain_replace_contacts(domain_object, new_admin_contact=None):
    """
    Detach all current contacts of the domain and attach new contact as admin role if required.
    """
    domain_object = domain_detach_contact(domain_object, 'admin')
    domain_object = domain_detach_contact(domain_object, 'billing')
    domain_object = domain_detach_contact(domain_object, 'tech')
    if new_admin_contact is not None:
        domain_object = domain_join_contact(domain_object, 'admin', new_admin_contact)
    return domain_object


def domain_set_auth_key(domain_object, new_auth_key):
    """
    Set mew aith_key for given domain
    """
    domain_object.auth_key = new_auth_key
    domain_object.save()
    logger.info('domain %r auth_key changed', domain_object.name)
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
    List all domains for given user identified by email.
    """
    existing_account = zusers.find_account(registrant_email)
    if not existing_account:
        return []
    return list(existing_account.domains.all().order_by('expiry_date'))


def list_domains_by_status(status):
    """
    List all domains for given domain status.
    """
    from back.models.domain import Domain

    return Domain.domains.filter(status=status)


def remove_inactive_domains(days=1):
    """
    Remove all inactive domains older than X days.
    """
    from back.models.domain import Domain

    given_days_before_create_date = timezone.now() - datetime.timedelta(days=days)

    inactive_domains = Domain.domains.filter(status='inactive', epp_id=None)
    domains_to_delete = inactive_domains.filter(
        Q(create_date__lt=given_days_before_create_date) | Q(create_date=None)
    )
    domains_to_delete.all().delete()
    return


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
                logger.info('nameserver host at position %d to be changed for %r : %s -> %s',
                             i, domain_object.name, existing_nameservers[i], hosts[i])
                domain_object.set_nameserver(i, hosts[i])
                domain_modified = True
        else:
            logger.info('nameserver host at position %d to be erased for %r', i, domain_object.name)
            domain_object.clear_nameserver(i)
            domain_modified = True
    if domain_modified:
        domain_object.save()
    return domain_modified

#------------------------------------------------------------------------------

def compare_contacts(domain_object, domain_info_response, target_contacts=None):
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
    new_contacts_dict = {}
    current_contacts_dict = {}
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

    for cur_contact_info in current_contacts:
        if cur_contact_info['type'] not in current_contacts_dict:
            current_contacts_dict[cur_contact_info['type']] = []
        current_contacts_dict[cur_contact_info['type']].append(cur_contact_info['id'])
        if len(current_contacts_dict[cur_contact_info['type']]) > 1:
            # remove secondary contacts for same role
            remove_contacts.append(cur_contact_info)

    for role, contact_object in target_contacts:
        if role == 'registrant':
            continue
        if not contact_object:
            continue
        if contact_object.owner != domain_object.owner:
            remove_contacts.append({'type': role, 'id': contact_object.epp_id, })
            continue
        if contact_object.epp_id:
            new_contacts.append({'type': role, 'id': contact_object.epp_id, })
            new_contacts_dict[role] = contact_object.epp_id

    for new_cont in new_contacts:
        if new_cont['type'] not in current_contacts_dict:
            if new_cont not in add_contacts:
                add_contacts.append(new_cont)
            continue
        if new_cont['id'] not in current_contacts_dict[new_cont['type']]:
            if new_cont not in add_contacts:
                add_contacts.append(new_cont)
            continue

    for old_cont in current_contacts:
        if old_cont['type'] not in new_contacts_dict:
            if old_cont not in remove_contacts:
                remove_contacts.append(old_cont)
            continue
        if new_contacts_dict[old_cont['type']] != old_cont['id']:
            if old_cont not in remove_contacts:
                remove_contacts.append(old_cont)
            continue

    #--- registrant
    current_registrant = None
    try:
        current_registrant = domain_info_response['epp']['response']['resData']['infData']['registrant']
    except:
        pass
    if domain_object.registrant and current_registrant and current_registrant != domain_object.registrant.epp_id:
        change_registrant = domain_object.registrant.epp_id
    logger.info('for %r found such changes: add_contacts=%r remove_contacts=%r change_registrant=%r',
                 domain_object.name, add_contacts, remove_contacts, change_registrant)
    return add_contacts, remove_contacts, change_registrant

#------------------------------------------------------------------------------

def response_to_datetime(field_name, domain_info_response):
    datetime_obj_naive = datetime.datetime.strptime(
        domain_info_response['epp']['response']['resData']['infData'][field_name],
        '%Y-%m-%dT%H:%M:%S.%fZ',
    )
    datetime_obj_local = timezone.get_current_timezone().localize(datetime_obj_naive)
    return datetime_obj_local

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
    try:
        epp_id = domain_info_response['epp']['response']['resData']['infData']['roid']
    except:
        logger.exception('Failed to read domain epp id from domain_info response')
        return False
    if not isinstance(epp_statuses, list):
        epp_statuses = [epp_statuses, ]
    for st in epp_statuses:
        new_domain_statuses[str(st['@s'])] = st['#text']
    modified = (sorted(current_domain_statuses.keys()) != sorted(new_domain_statuses.keys()))
    updated = False
    old_domain_status = domain_object.status
    if modified:
        domain_object.epp_statuses = new_domain_statuses
        updated = True
    if epp_id and domain_object.epp_id != epp_id:
        domain_object.epp_id = epp_id
        updated = True
    if 'ok' in new_domain_statuses:
        if domain_object.status != 'active':
            domain_object.status = 'active'
            updated = True
    else:
        new_domain_status = 'inactive'
        if 'serverHold' in new_domain_statuses:
            new_domain_status = 'suspended'
        if 'pendingDelete' in new_domain_statuses:
            new_domain_status = 'to_be_deleted'
        if 'pendingRestore' in new_domain_statuses:
            # TODO: check that flow
            new_domain_status = 'to_be_restored'
        # TODO: continue with other statuses: https://www.icann.org/resources/pages/epp-status-codes-2014-06-16-en
        if domain_object.status != new_domain_status:
            domain_object.status = new_domain_status
            updated = True
    if updated:
        if save:
            domain_object.save()
        logger.info('domain %r status updated from EPP response: %r -> %r',
                    domain_object, old_domain_status, domain_object.status)
    else:
        logger.info('no changes in domain status were detected for %r', domain_object)
    if modified:
        logger.info('domain %r new status is %r because EPP statuses modified:  %r -> %r',
                    domain_object, domain_object.status, current_domain_statuses, new_domain_statuses)
    return updated

#------------------------------------------------------------------------------

def generate_random_auth_info(length=12):
    """
    Generates a new random auth info code with lowercase / uppercase letters and digits.
    """
    random.seed()
    lower_length = int(length / 3)
    upper_length = int(length / 3)
    digits_lendth = length - upper_length - lower_length
    lower_pwd = [random.choice(string.ascii_lowercase) for _ in range(lower_length)]
    upper_pwd = [random.choice(string.ascii_uppercase) for _ in range(upper_length)]
    digits_pwd = [random.choice(string.digits) for _ in range(digits_lendth)]
    pwd = lower_pwd + upper_pwd + digits_pwd
    random.shuffle(pwd)
    return ''.join(pwd)

#------------------------------------------------------------------------------
