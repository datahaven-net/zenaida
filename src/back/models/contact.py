from django.db import models

from back.models.profile import Profile


class Contact(models.Model):
    
    contacts = models.Manager()

    # related fields:
    # registrant_domains -> back.models.domain.Domain
    # admin_domains -> back.models.domain.Domain
    # billing_domains -> back.models.domain.Domain
    # tech_domains -> back.models.domain.Domain

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='contacts', )

    epp_id = models.CharField(max_length=32, unique=True, )

    def __str__(self):
        return 'Contact({})'.format(self.epp_id)
