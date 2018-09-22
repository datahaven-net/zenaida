import re
import datetime

from django.utils import timezone
from django.core import exceptions

from main import settings

from back.models.domain import Domain
from back.models.registrar import Registrar

from back import zones


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


def is_exist(domain):
    """
    Return `True` if domain exists, doing query in Domain table.
    """
    return bool(Domain.domains.filter(name=domain).first())


def find(domain):
    """
    Return `Domain` object if found in Domain table, else None.
    """
    return Domain.domains.filter(name=domain).first()


def create(name, expiry_date=None, create_date=None, epp_id=None, auth_key=None, registrar=None,
           registrant=None, contact_admin=None, contact_billing=None, contact_tech=None, ):
    """
    Create new domain.
    """
    if not create_date:
        create_date = timezone.now()
    if not expiry_date:
        expiry_date = timezone.now() + datetime.timedelta(days=365)
    if not contact_admin and not contact_tech and not contact_billing:
        raise ValueError('Must be set at least one of the domain contacts')
    if not registrant:
        registrant = [c for c in filter(None, [contact_admin, contact_tech, contact_billing, ])][0]
    domain_obj = Domain(
        name=name,
        expiry_date=expiry_date,
        create_date=create_date,
        epp_id=epp_id,
        auth_key=auth_key,
    )
    domain_obj.zone = zones.make(domain_obj.tld_zone)
    if not isinstance(registrar, Registrar):
        registrar = Registrar.registrars.get_or_create(
            epp_id=(registrar or settings.DEFAULT_REGISTRAR_ID),
        )[0]
    domain_obj.registrar = registrar
    if registrant:
        domain_obj.registrant = registrant
    if contact_admin:
        domain_obj.contact_admin = contact_admin
    if contact_tech:
        domain_obj.contact_tech = contact_tech
    if contact_billing:
        domain_obj.contact_billing = contact_billing
    domain_obj.save()
    return domain_obj
