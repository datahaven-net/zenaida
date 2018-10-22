import logging
import re

from django.utils import timezone

from main import settings

from back.models.domain import Domain
from back.models.registrar import Registrar
from back.models.nameserver import NameServer

from back import zones
from back import users

logger = logging.getLogger(__name__)


def is_valid(domain, idn=False):
    """
    Return `True` if domain name is valid.
    """
    regexp = '^[\w\-\.]*$'
    regexp_IP = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'
    if re.match(regexp, domain) is None:
        return False
    if domain.startswith('-'):
        # -abcd.ai is not a valid name
        return False
    if not idn and domain.count('--'):
        # IDN domains are not allowed
        return False
    if len(domain) >= 4 and domain[2] == '.' and domain[1] == '-':
        # x-.com is not valid name
        return False
    if domain.count('-.'):
        # abcd-.com is not a valid name
        return False
    if domain.startswith('.'):
        # .abc.com is not a valid name
        return False
    if domain.endswith('.'):
        # abc.com. is not a valid name
        return False
    if domain.count('_.'):
        # xyz_.net is not a valid name
        return False
    if domain.startswith('_'):
        # _asdf.org is not a valid name
        return False
    if re.match(regexp_IP, domain.strip()) is not None:
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
        name,
        owner,
        expiry_date=None,
        create_date=None,
        epp_id='',
        auth_key='',
        registrar=None,
        registrant=None,
        contact_admin=None,
        contact_billing=None,
        contact_tech=None,
        hosts=[],
    ):
    """
    Create new domain.
    """
    if is_exist(domain_name=name, epp_id=epp_id):
        raise ValueError('Domain already exists')
    if not create_date:
        create_date = timezone.now()
    if not contact_admin and not contact_tech and not contact_billing:
        raise ValueError('Must be set at least one of the domain contacts')
    if not registrant:
        registrant = [c for c in filter(None, [contact_admin, contact_tech, contact_billing, ])][0]
    new_domain = Domain(
        name=name,
        owner=owner,
        expiry_date=expiry_date,
        create_date=create_date,
        epp_id=epp_id,
        auth_key=auth_key,
    )
    new_domain.zone = zones.make(new_domain.tld_zone)
    if not isinstance(registrar, Registrar):
        registrar = Registrar.registrars.get_or_create(
            epp_id=(registrar or settings.DEFAULT_REGISTRAR_ID),
        )[0]
    new_domain.registrar = registrar
    if registrant:
        new_domain.registrant = registrant
    if contact_admin:
        new_domain.contact_admin = contact_admin
    if contact_tech:
        new_domain.contact_tech = contact_tech
    if contact_billing:
        new_domain.contact_billing = contact_billing
    host_position = 1
    for host in hosts:
        new_nameserver = create_nameserver(host=host, owner=owner)
        new_domain.set_nameserver(host_position, new_nameserver)
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
    return existing_account.domains


def create_nameserver(host, owner, epp_id=''):
    """
    Create new nameserver.
    """
    if epp_id:
        existing_nameserver = NameServer.nameservers.filter(epp_id=epp_id).first()
        if existing_nameserver:
            logger.debug('nameserver with epp_id=%s already exist', epp_id)
            return existing_nameserver
    new_nameserver = NameServer.nameservers.create(host=host, owner=owner, epp_id=epp_id)
    logger.debug('nameserver created: %s', new_nameserver)
    return new_nameserver
