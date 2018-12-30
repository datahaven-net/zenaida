from django.forms import forms, fields, models, TextInput

from back.models.profile import Profile


class DomainLookupForm(forms.Form):
    domain_name = fields.CharField(label='', max_length=100, required=True,
                                   widget=TextInput(attrs={'placeholder': 'Find your domain'}),)


class DomainCreateForm(forms.Form):
    domain_name = fields.CharField(label='Domain Name', max_length=100, required=True)


class DomainAddForm(forms.Form):
    domain_name = fields.CharField(label='Domain Add', max_length=100, required=True)
    contact_admin = fields.CharField(label='Contact Admin', max_length=100, required=False)
    contact_billing = fields.CharField(label='Contact Billing', max_length=100, required=False)
    contact_tech = fields.CharField(label='Contact Tech', max_length=100, required=False)


class AccountProfileForm(models.ModelForm):

    class Meta:
        model = Profile
        fields = (
            'contact_email',
            'contact_voice',
            'contact_fax',
            'person_name',
            'organization_name',
            'address_street',
            'address_city',
            'address_province',
            'address_postal_code',
            'address_country',
        )
