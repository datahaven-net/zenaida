from django.db import models
from django.core import exceptions

from accounts.models.account import Account

from back.models.zone import Zone
from back.models.contact import Contact
from back.models.registrar import Registrar


def validate(domain):
    """
    Raise `ValidationError()` if domain 
    """
    from back.domains import is_valid
    if is_valid(domain):
        return True
    raise exceptions.ValidationError('value "{}" is not a valid domain name'.format(domain))


class Domain(models.Model):

    domains = models.Manager()

    name = models.CharField(max_length=255, unique=True, validators=[validate, ])

    expiry_date = models.DateTimeField()
    create_date = models.DateTimeField()

    epp_id = models.CharField(max_length=32, unique=True, blank=True)

    auth_key = models.CharField(max_length=64, blank=True)

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='domains', )

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='domains', )

    registrar = models.ForeignKey(Registrar, on_delete=models.CASCADE, related_name='domains', null=True, blank=True, )

    registrant = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='registrant_domains', null=True, blank=True, )
    contact_admin = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='admin_domains', null=True, blank=True, )
    contact_billing = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='billing_domains', null=True, blank=True, )
    contact_tech = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='tech_domains', null=True, blank=True, )

    @property
    def tld_name(self):
        return self.name.split('.')[0]

    @property
    def tld_zone(self):
        return '.'.join(self.name.split('.')[1:])

    def __str__(self):
        return 'Domain({}:{})'.format(self.name, self.epp_id)
