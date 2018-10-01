from django.db import models

from accounts.models.account import Account


class Activation(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=20)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='activations', )

    def __str__(self):
        return 'Activation({})'.format(self.account.email)
