from django.db import models

from back.models.profile import Profile


class Contact(models.Model):
    
    contacts = models.Manager()

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='contacts', )

    epp_id = models.CharField(max_length=32, unique=True, )

    def __str__(self):
        return 'Contact({})'.format(self.epp_id)
