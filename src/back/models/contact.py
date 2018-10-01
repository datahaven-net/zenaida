from django.db import models

from accounts.models.account import Account


class Contact(models.Model):
    
    contacts = models.Manager()

    # related fields:
    # registrant_domains -> back.models.domain.Domain
    # admin_domains -> back.models.domain.Domain
    # billing_domains -> back.models.domain.Domain
    # tech_domains -> back.models.domain.Domain

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='contacts', )

    epp_id = models.CharField(max_length=32, unique=True, null=True, )

    person_name = models.CharField(max_length=255, default='', blank=True,)
    organization_name = models.CharField(max_length=255, default='', blank=True,)

    address_street = models.CharField(max_length=255, default='', blank=True,)
    address_city = models.CharField(max_length=255, default='', blank=True,)
    address_province = models.CharField(max_length=255, default='', blank=True,)
    address_postal_code = models.CharField(max_length=255, default='', blank=True,)
    address_country = models.CharField(max_length=255, default='', blank=True,)

    contact_voice = models.CharField(max_length=255, default='', blank=True,)
    contact_fax = models.CharField(max_length=255, default='', blank=True,)
    contact_email = models.CharField(max_length=255, default='', blank=True,)

    def __str__(self):
        return 'Contact({})'.format(self.epp_id)
