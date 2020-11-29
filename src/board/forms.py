from django import forms


class DomainSyncForm(forms.Form):
    domain_name = forms.fields.CharField(label='Domain Name')
