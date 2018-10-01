from django.db import models

from back.models.account import Account


class Profile(models.Model):

    profiles = models.Manager()

    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile')

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
        return 'Profile({})'.format(self.account.email)
