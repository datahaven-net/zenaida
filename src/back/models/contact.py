from django.db import models

from back.models.profile import Profile


class Contact(models.Model):
    
    objects = models.Manager()

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='contacts', )

    epp_id = models.CharField(max_length=32, unique=True, )
