from django.db import models

from back.models.profile import Profile
from back.models.zone import Zone
from back.models.contact import Contact
from back.models.registrar import Registrar


class Domain(models.Model):

    objects = models.Manager()

    name = models.CharField(max_length=255)

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='domains', )

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='domains', )

    registrar = models.ForeignKey(Registrar, on_delete=models.CASCADE, related_name='domains', )

    registrant = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='domains', )

    contact_admin = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='+', )
    contact_billing = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='+', )
    contact_tech = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='+', )

    epp_id = models.CharField(max_length=32, unique=True, )

    auth_key = models.CharField(max_length=64)


    @property
    def tld(self):
        return '{}.{}'.format(self.name, self.zone.name)
