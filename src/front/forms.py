from django.forms import forms, fields

class DomainLookupForm(forms.Form):
    domain_name = fields.CharField(label='domain name', max_length=100, required=False)
