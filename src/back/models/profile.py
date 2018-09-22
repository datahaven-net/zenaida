from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from back.models.account import Account


class Profile(models.Model):

    profiles = models.Manager()

    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile')

    person_name = models.CharField(max_length=255, default='')
    organization_name = models.CharField(max_length=255, default='')

    address_street = models.CharField(max_length=255, default='')
    address_city = models.CharField(max_length=255, default='')
    address_province = models.CharField(max_length=255, default='')
    address_postal_code = models.CharField(max_length=255, default='')
    address_country = models.CharField(max_length=255, default='')

    contact_voice = models.CharField(max_length=255, default='')
    contact_fax = models.CharField(max_length=255, default='')
    contact_email = models.CharField(max_length=255, default='')

    def __str__(self):
        return 'Profile({})'.format(self.account.email)


@receiver(post_save, sender=Account)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(account=instance)


@receiver(post_save, sender=Account)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
