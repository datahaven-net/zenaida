from django.db import models


class Registrar(models.Model):

    objects = models.Manager()

    name = models.CharField(max_length=255)

    epp_id = models.CharField(max_length=32, unique=True, )
