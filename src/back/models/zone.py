from django.db import models


class Zone(models.Model):

    zones = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'zones'
        default_manager_name = 'zones'

    # related fields:
    # domains -> back.models.domain.Domain

    name = models.CharField(max_length=255, unique=True, )

    def __str__(self):
        return 'Zone({})'.format(self.name.upper())

    def __repr__(self):
        return 'Zone({})'.format(self.name.upper())
