from django.db import models


class Registrar(models.Model):

    registrars = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'registrars'
        default_manager_name = 'registrars'

    # related fields:
    # domains -> back.models.domain.Domain

    epp_id = models.CharField(max_length=32, unique=True, blank=True, default=None, )

    def __str__(self):
        return 'Registrar({})'.format(self.epp_id)

    def __repr__(self):
        return 'Registrar({})'.format(self.epp_id)
