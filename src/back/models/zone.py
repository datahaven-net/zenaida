from django.db import models


class Zone(models.Model):

    zones = models.Manager()

    name = models.CharField(max_length=255, unique=True, )

    def __str__(self):
        return 'Zone({})'.format(self.name.upper())
