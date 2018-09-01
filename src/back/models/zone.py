from django.db import models


class Zone(models.Model):

    objects = models.Manager()

    name = models.CharField(max_length=255)
