from django.db import models

from back.models.account import Account


class Activation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=20)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='activations', )
