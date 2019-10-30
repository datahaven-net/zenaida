from django.core.validators import validate_email
from django.db import models

from accounts.models.account import Account
from back.validators import phone_regex, CountryField


class Profile(models.Model):

    profiles = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'profiles'
        default_manager_name = 'profiles'

    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile')

    person_name = models.CharField(max_length=255, verbose_name='Full Name')
    organization_name = models.CharField(max_length=255, verbose_name='Organization')

    address_street = models.CharField(max_length=255, verbose_name='Street address')
    address_city = models.CharField(max_length=255, verbose_name='City')
    address_province = models.CharField(max_length=255, verbose_name='Province')
    address_postal_code = models.CharField(max_length=255, verbose_name='ZIP code')
    address_country = CountryField(verbose_name='Country')

    contact_voice = models.CharField(validators=[phone_regex], max_length=17, blank=True, verbose_name='Mobile')
    contact_fax = models.CharField(validators=[phone_regex], max_length=17, blank=True, verbose_name='Fax')
    contact_email = models.CharField(validators=[validate_email], max_length=255, verbose_name='Email')

    email_notifications_enabled = models.BooleanField(verbose_name='Email notifications', default=True)

    def __str__(self):
        return 'Profile({})'.format(self.account.email)

    def is_complete(self):
        # TODO: extra regex validators to be added later
        if not self.person_name:
            return False
        if not self.organization_name:
            return False
        if not self.address_street:
            return False
        if not self.address_city:
            return False
        if not self.address_postal_code:
            return False
        if not self.address_country:
            return False
        if not self.contact_voice:
            return False
        if not self.contact_email:
            return False
        return True
