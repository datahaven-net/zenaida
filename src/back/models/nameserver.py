from django.db import models

from accounts.models.account import Account


class NameServer(models.Model):
    
    nameservers = models.Manager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'nameservers'
        default_manager_name = 'nameservers'

    # related fields:
    # domains1 -> back.models.domain.Domain
    # domains2 -> back.models.domain.Domain
    # domains3 -> back.models.domain.Domain
    # domains4 -> back.models.domain.Domain

    host = models.CharField(max_length=255, unique=True, )

    epp_id = models.CharField(max_length=32, unique=True, blank=True, default='')

    owner = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='nameservers', )

    def __str__(self):
        return 'NameServer({}:{})'.format(self.host, self.epp_id)
