from django.core.validators import validate_email
from django.db import models

from accounts.models.account import Account
from back.validators import CountryField, phone_regex


class Contact(models.Model):
    
    contacts = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'contacts'
        default_manager_name = 'contacts'

    # related fields:
    # admin_domains -> back.models.domain.Domain
    # billing_domains -> back.models.domain.Domain
    # tech_domains -> back.models.domain.Domain

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='contacts', )

    epp_id = models.CharField(max_length=32, unique=True, null=True, blank=True, default=None)

    person_name = models.CharField(max_length=255, verbose_name='Full Name')
    organization_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Organization')

    address_street = models.CharField(max_length=255, verbose_name='Street address')
    address_city = models.CharField(max_length=255, verbose_name='City')
    address_province = models.CharField(max_length=255, blank=True, null=True, verbose_name='Province')
    address_postal_code = models.CharField(max_length=255, blank=True, null=True, verbose_name='ZIP code')
    address_country = CountryField(verbose_name='Country')

    contact_voice = models.CharField(validators=[phone_regex], max_length=17, verbose_name='Mobile')
    contact_fax = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True, verbose_name='Fax')
    contact_email = models.CharField(validators=[validate_email], max_length=255, verbose_name='Email')

    def __str__(self):
        return 'Contact({} {})'.format(self.owner.email, self.epp_id or '?')

    def __repr__(self):
        return 'Contact({} {})'.format(self.owner.email, self.epp_id or '?')

    def save(self, *args, **kwargs):
        if not self.epp_id:
            self.epp_id = None
        super(Contact, self).save(*args, **kwargs)

    @property
    def label(self):
        if not self.organization_name:
            return self.person_name
        return '{} / {}'.format(self.person_name, self.organization_name)

    @property
    def address_full(self):
        addr = f'{self.address_street or ""} {self.address_city or ""}'
        if self.address_province or self.address_postal_code:
            addr += f', {self.address_province or ""} {self.address_postal_code or ""}'
        addr += f', {self.address_country or ""}'
        return addr

    @property
    def has_any_domains(self):
        return bool(self.admin_domains.first() or self.billing_domains.first() or self.tech_domains.first())


class Registrant(models.Model):
    
    registrants = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'registrants'
        default_manager_name = 'registrants'

    # related fields:
    # registrant_domains -> back.models.domain.Domain

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='registrants', )

    epp_id = models.CharField(max_length=32, unique=True, null=True, blank=True, default=None)

    person_name = models.CharField(max_length=255, verbose_name='Full Name')
    organization_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Organization')

    address_street = models.CharField(max_length=255, verbose_name='Street address')
    address_city = models.CharField(max_length=255, verbose_name='City')
    address_province = models.CharField(max_length=255, blank=True, null=True, verbose_name='Province')
    address_postal_code = models.CharField(max_length=255, blank=True, null=True, verbose_name='ZIP code')
    address_country = CountryField(verbose_name='Country')

    contact_voice = models.CharField(validators=[phone_regex], max_length=17, verbose_name='Mobile')
    contact_fax = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True, verbose_name='Fax')
    contact_email = models.CharField(validators=[validate_email], max_length=255, verbose_name='Email')

    def __str__(self):
        return 'Registrant({} {})'.format(self.owner.email, self.epp_id or '?')

    def __repr__(self):
        return 'Registrant({} {})'.format(self.owner.email, self.epp_id or '?')

    def save(self, *args, **kwargs):
        if not self.epp_id:
            self.epp_id = None
        super(Registrant, self).save(*args, **kwargs)

    @property
    def has_any_domains(self):
        return bool(self.registrant_domains.first())
