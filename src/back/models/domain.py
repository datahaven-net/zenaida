import logging

from django.db import models

from accounts.models.account import Account

from back.domains import validate

from back.models.zone import Zone
from back.models.contact import Contact, Registrant
from back.models.registrar import Registrar

logger = logging.getLogger(__name__)


class Domain(models.Model):

    domains = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'domains'
        default_manager_name = 'domains'
        ordering = ['expiry_date']

    name = models.CharField(max_length=255, unique=True, validators=[validate, ])

    expiry_date = models.DateTimeField()
    create_date = models.DateTimeField()

    epp_id = models.CharField(max_length=32, unique=True, null=True, default=None)
    epp_status = models.CharField(
        max_length=32,
        choices=(
            ('inactive', 'INACTIVE', ),
            ('deactivated', 'DEACTIVATED', ),
            ('client_hold', 'CLIENT HOLD', ),
            ('server_hold', 'SERVER HOLD', ),
            ('to_be_deleted', 'TO BE DELETED', ),
            ('to_be_restored', 'TO BE RESTORED', ),
            ('unknown', 'UNKNOWN', ),
            ('active', 'ACTIVE', ),
        ),
        default='inactive',
    )

    auth_key = models.CharField(max_length=64, blank=True, default='')

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='domains')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='domains')

    registrar = models.ForeignKey(Registrar, on_delete=models.CASCADE, related_name='domains', null=True, blank=True)

    registrant = models.ForeignKey(
        Registrant, on_delete=models.CASCADE, related_name='registrant_domains', null=True, blank=True)

    contact_admin = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='admin_domains', null=True, blank=True, verbose_name='Administrative')
    contact_billing = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='billing_domains', null=True, blank=True, verbose_name='Billing')
    contact_tech = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='tech_domains', null=True, blank=True, verbose_name='Technical')

    nameserver1 = models.CharField(max_length=256, blank=True, default='', verbose_name='Nameserver 1')
    nameserver2 = models.CharField(max_length=256, blank=True, default='', verbose_name='Nameserver 2')
    nameserver3 = models.CharField(max_length=256, blank=True, default='', verbose_name='Nameserver 3')
    nameserver4 = models.CharField(max_length=256, blank=True, default='', verbose_name='Nameserver 4')

    @property
    def tld_name(self):
        return self.name.split('.')[0]

    @property
    def tld_zone(self):
        return '.'.join(self.name.split('.')[1:])

    @property
    def expiry_datetime_as_date(self):
        return self.expiry_date.date()

    @property
    def create_datetime_as_date(self):
        return self.create_date.date()

    def __str__(self):
        return 'Domain({}:{}:{})'.format(self.name, self.epp_id, self.owner.email)

    def list_contacts(self):
        """
        Return list of 4 tuples containing contact and its role for given domain.
        Always returns list of 4 tuples, empty contact means contact was not set for that role.
        """
        return [
            ('admin', self.contact_admin, ),
            ('billing', self.contact_billing, ),
            ('tech', self.contact_tech, ),
        ]

    def list_nameservers(self):
        """
        Return list of current nameservers.
        Always returns list of 4 items, empty string means nameserver was not set.
        """
        return [
            self.nameserver1,
            self.nameserver2,
            self.nameserver3,
            self.nameserver4,
        ]

    def get_nameserver(self, pos):
        """
        Return nameserver value from given position.
        Counting `pos` from 0 to 3.
        """
        if pos == 0:
            return self.nameserver1
        if pos == 1:
            return self.nameserver2
        if pos == 2:
            return self.nameserver3
        if pos == 3:
            return self.nameserver4
        raise ValueError('Invalid position for nameserver')

    def set_nameserver(self, pos, nameserver):
        """
        Set nameserver on given position.
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
        Set empty value for nameserver at given position.
        Counting `pos` from 0 to 3.
        """
        if pos not in list(range(4)):
            raise ValueError('Invalid position for nameserver')
        if pos == 0 and self.nameserver1:
            logger.debug('nameserver %s to be erased for %s at position 1', self.nameserver1, self)
            self.nameserver1 = ''
            return True
        if pos == 1 and self.nameserver2:
            logger.debug('nameserver %s to be erased for %s at position 2', self.nameserver2, self)
            self.nameserver2 = ''
            return True
        if pos == 2 and self.nameserver3:
            logger.debug('nameserver %s to be erased for %s at position 3', self.nameserver3, self)
            self.nameserver3 = ''
            return True
        if pos == 3 and self.nameserver4:
            logger.debug('nameserver %s to be erased for %s at position 4', self.nameserver4, self)
            self.nameserver4 = ''
            return True
        return False

    @property
    def is_registered(self):
        return bool(self.epp_id)

    @property
    def can_be_restored(self):
        return bool(self.epp_id) and self.epp_status != 'active'
