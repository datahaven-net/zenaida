from django.forms import forms, fields, models, TextInput

from back.models.profile import Profile


class DomainLookupForm(forms.Form):
    domain_name = fields.CharField(label='Domain Name', widget=TextInput(attrs={'placeholder': 'Find your name'}),
                                   max_length=100, required=True)


class DomainCreateForm(forms.Form):
    domain_name = fields.CharField(label='Domain Name', max_length=100, required=True)


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
