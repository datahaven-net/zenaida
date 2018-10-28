import logging

from django.db import models
from django.core import exceptions

from accounts.models.account import Account

from back.models.zone import Zone
from back.models.contact import Contact
from back.models.registrar import Registrar
from back.models.nameserver import NameServer

logger = logging.getLogger(__name__)


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

    class Meta:
        app_label = 'back'
        base_manager_name = 'domains'
        default_manager_name = 'domains'

    name = models.CharField(max_length=255, unique=True, validators=[validate, ])

    expiry_date = models.DateTimeField()
    create_date = models.DateTimeField()

    epp_id = models.CharField(max_length=32, unique=True, blank=True, default='')

    auth_key = models.CharField(max_length=64, blank=True, default='')

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='domains', )

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='domains', )

    registrar = models.ForeignKey(Registrar, on_delete=models.CASCADE, related_name='domains', null=True, blank=True, )

    registrant = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='registrant_domains', null=True, blank=True, )
    contact_admin = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='admin_domains', null=True, blank=True, )
    contact_billing = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='billing_domains', null=True, blank=True, )
    contact_tech = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='tech_domains', null=True, blank=True, )

    nameserver1 = models.ForeignKey(NameServer, on_delete=models.CASCADE, related_name='domains1', null=True, blank=True, )
    nameserver2 = models.ForeignKey(NameServer, on_delete=models.CASCADE, related_name='domains2', null=True, blank=True, )
    nameserver3 = models.ForeignKey(NameServer, on_delete=models.CASCADE, related_name='domains3', null=True, blank=True, )
    nameserver4 = models.ForeignKey(NameServer, on_delete=models.CASCADE, related_name='domains4', null=True, blank=True, )

    @property
    def tld_name(self):
        return self.name.split('.')[0]

    @property
    def tld_zone(self):
        return '.'.join(self.name.split('.')[1:])

    def __str__(self):
        return 'Domain({}:{})'.format(self.name, self.epp_id)

    def list_hosts(self):
        """
        Return list of current hosts from NameServer objects.
        Always returns list of 4 items, empty string means nameserver was not set.
        """
        l = ['', ] * 4
        if self.nameserver1:
            l[0] = self.nameserver1.host
        if self.nameserver2:
            l[1] = self.nameserver2.host
        if self.nameserver3:
            l[2] = self.nameserver3.host
        if self.nameserver4:
            l[3] = self.nameserver4.host
        return l
    
    def list_nameservers(self):
        """
        Return list of current NameServer objects.
        Always returns list of 4 items, None means nameserver was not set at given position.
        """
        l = [None, ] * 4
        if self.nameserver1:
            l[0] = self.nameserver1
        if self.nameserver2:
            l[1] = self.nameserver2
        if self.nameserver3:
            l[2] = self.nameserver3
        if self.nameserver4:
            l[3] = self.nameserver4
        return l

    def get_nameserver(self, pos):
        """
        Return NameServer object from given position.
        Counting `pos` from 1 to 4.
        """
        if pos == 1:
            return self.nameserver1
        if pos == 2:
            return self.nameserver2
        if pos == 3:
            return self.nameserver3
        if pos == 4:
            return self.nameserver4
        raise ValueError('Invalid position for nameserver')

    def set_nameserver(self, pos, nameserver):
        """
        Set NameServer object on given position.
        Counting `pos` from 0 to 3.
        """
        if pos == 0:
            self.nameserver1 = nameserver
            logger.debug('nameserver %s set for %s at position 1', nameserver, self)
            return
        if pos == 1:
            self.nameserver2 = nameserver
            logger.debug('nameserver %s set for %s at position 2', nameserver, self)
            return
        if pos == 2:
            self.nameserver3 = nameserver
            logger.debug('nameserver %s set for %s at position 3', nameserver, self)
            return
        if pos == 3:
            self.nameserver4 = nameserver
            logger.debug('nameserver %s set for %s at position 4', nameserver, self)
            return
        raise ValueError('Invalid position for nameserver')

    def clear_nameserver(self, pos):
        """
        Remove NameServer object at given position.
        Counting `pos` from 0 to 3.
        """
        if pos not in list(range(4)):
            raise ValueError('Invalid position for nameserver')
        if pos == 0 and self.nameserver1:
            logger.debug('nameserver %s to be erased for %s at position 1', self.nameserver1, self)
            self.nameserver1.delete()
            return True
        if pos == 1 and self.nameserver2:
            logger.debug('nameserver %s to be erased for %s at position 2', self.nameserver1, self)
            self.nameserver2.delete()
            return True
        if pos == 2 and self.nameserver3:
            logger.debug('nameserver %s to be erased for %s at position 3', self.nameserver1, self)
            self.nameserver3.delete()
            return True
        if pos == 3 and self.nameserver4:
            logger.debug('nameserver %s to be erased for %s at position 4', self.nameserver1, self)
            self.nameserver4.delete()
            return True
        return False
