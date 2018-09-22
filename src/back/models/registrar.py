from django.db import models


class Registrar(models.Model):

    registrars = models.Manager()

    epp_id = models.CharField(max_length=32, unique=True, )
