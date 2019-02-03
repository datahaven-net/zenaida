from django.db import models

from accounts.models.account import Account


class Contact(models.Model):
    
    contacts = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'contacts'
        default_manager_name = 'contacts'

    # related fields:
    # registrant_domains -> back.models.domain.Domain
    # admin_domains -> back.models.domain.Domain
    # billing_domains -> back.models.domain.Domain
    # tech_domains -> back.models.domain.Domain

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='contacts', )

    epp_id = models.CharField(max_length=32, unique=True, null=True, blank=True, default=None)

    person_name = models.CharField(max_length=255, default='', blank=True, verbose_name='Full Name')
    organization_name = models.CharField(max_length=255, default='', blank=True, verbose_name='Organization')

    address_street = models.CharField(max_length=255, default='', blank=True, verbose_name='Street address')
    address_city = models.CharField(max_length=255, default='', blank=True, verbose_name='City')
    address_province = models.CharField(max_length=255, default='', blank=True, verbose_name='Province')
    address_postal_code = models.CharField(max_length=255, default='', blank=True, verbose_name='ZIP code')
    address_country = models.CharField(max_length=255, default='', blank=True, verbose_name='Country')

    contact_voice = models.CharField(max_length=255, default='', blank=True, verbose_name='Mobile')
    contact_fax = models.CharField(max_length=255, default='', blank=True, verbose_name='Fax')
    contact_email = models.CharField(max_length=255, default='', blank=True, verbose_name='Email')

    def __str__(self):
        return 'Contact ({} {})'.format(self.owner.email, self.epp_id)

    @property
    def label(self):
        return '{} / {}'.format(self.person_name, self.organization_name)

    @property
    def address_full(self):
        return f'{self.address_street} {self.address_city}, {self.address_province} {self.address_postal_code}, {self.address_country}'
