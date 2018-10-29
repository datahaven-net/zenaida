import logging
import re

from django.utils import timezone

from main import settings

from back.models.domain import Domain
from back.models.registrar import Registrar

from back import zones
from back import users

logger = logging.getLogger(__name__)


def is_valid(domain_name, idn=False):
    """
    Return `True` if domain name is valid.
    """
    regexp = '^[\w\-\.]*$'
    regexp_IP = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'
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


def is_exist(domain_name='', epp_id=''):
    """
    Return `True` if domain exists, doing query in Domain table.
    """
    if epp_id:
        return bool(Domain.domains.filter(epp_id=epp_id).first())
    return bool(Domain.domains.filter(name=domain_name).first())


def find(domain_name='', epp_id=''):
    """
    Return `Domain` object if found in Domain table, else None.
    """
    if epp_id:
        return Domain.domains.filter(epp_id=epp_id).first()
    return Domain.domains.filter(name=domain_name).first()


def create(
        domain_name,
        owner,
        expiry_date=None,
        create_date=None,
        epp_id='',
        auth_key='',
        registrar=None,
        registrant=None,
        contact_admin=None,
        contact_tech=None,
        contact_billing=None,
        nameservers=[],
    ):
    """
    Create new domain.
    """
    if is_exist(domain_name=domain_name, epp_id=epp_id):
        raise ValueError('Domain already exists')
    if not create_date:
        create_date = timezone.now()
    if not contact_admin and not contact_tech and not contact_billing:
        raise ValueError('Must be set at least one of the domain contacts')
    if not registrant:
        registrant = [c for c in filter(None, [contact_admin, contact_tech, contact_billing, ])][0]
    if not isinstance(registrar, Registrar):
        registrar = Registrar.registrars.get_or_create(
            epp_id=(registrar or settings.DEFAULT_REGISTRAR_ID),
        )[0]
    zone = zones.make('.'.join(domain_name.split('.')[1:]))
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
        new_domain.set_nameserver(host_position, nameserver)
        host_position += 1
    new_domain.save()
    logger.debug('domain created: %s', new_domain)
    return new_domain


def list_domains(registrant_email):
    """
    List all domains for given user identified by email where he have registrant role assigned.
    """
    existing_account = users.find_account(registrant_email)
    if not existing_account:
        return []
    return list(existing_account.domains.all())


def update_nameservers(domain_name, hosts):
    """
    Create or update nameservers hosts for given domain.
    Value `hosts` is a list of 4 items.
    None or empty string in the list means nameserver not set at given position.
    """
    existing_domain = find(domain_name=domain_name)
    if not existing_domain:
        raise ValueError('Domain not exist')
    existing_nameservers = existing_domain.list_nameservers()
    domain_modified = False
    for i in range(len(hosts)):
        if hosts[i]:
            if existing_nameservers[i] != hosts[i]:
                logger.debug('nameserver host to be changed for %s : %s -> %s',
                             existing_domain, existing_nameservers[i], hosts[i])
                existing_domain.set_nameserver(i, hosts[i])
                domain_modified = True
        else:
            existing_domain.clear_nameserver(i)
            domain_modified = True
    if domain_modified:
        existing_domain.save()
    return domain_modified
