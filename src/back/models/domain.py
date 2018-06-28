from django.db import models

from back.models.profile import Profile


class Domain(models.Model):

    objects = models.Manager()

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='domains', )
    
    name = models.CharField(max_length=255)
