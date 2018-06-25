from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    person_first_name = models.CharField(max_length=255, default='')

    person_last_name = models.CharField(max_length=255, default='')

    organization_name = models.CharField(max_length=255, default='')

    address_street = models.CharField(max_length=255, default='')

    address_city = models.CharField(max_length=255, default='')

    address_province = models.CharField(max_length=255, default='')

    address_postal_code = models.CharField(max_length=255, default='')

    address_country = models.CharField(max_length=255, default='')

    contact_voice = models.CharField(max_length=255, default='')

    contact_fax = models.CharField(max_length=255, default='')

    contact_email = models.CharField(max_length=255, default='')


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
