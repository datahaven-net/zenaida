import re

from django.core import exceptions

from back.models.domain import Domain


def is_valid(domain, parent='', idn=False):
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


def validate(domain):
    """
    Raise `ValidationError()` if domain 
    """
    if is_valid(domain):
        return True
    raise exceptions.ValidationError('value "{}" is not a valid domain name'.format(domain))


def is_exist(domain):
    """
    Return `True` if domain exists, doing query in Domain table.
    """
    return bool(Domain.domains.filter(name=domain).first())


def take(domain):
    """
    Return `Domain` object if found in Domain table, else None.
    """
    return Domain.domains.filter(name=domain).first()
