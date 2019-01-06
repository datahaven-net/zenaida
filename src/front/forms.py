from django.forms import forms, fields, models, ModelForm, TextInput
from back.models.profile import Profile
from back.models.domain import Contact, Domain


class DomainLookupForm(forms.Form):
    domain_name = fields.CharField(label='', max_length=100, required=True,
                                   widget=TextInput(attrs={'placeholder': 'Find your domain'}),)


class DomainCreateForm(forms.Form):
    domain_name = fields.CharField(label='Domain Name', max_length=100, required=True)


class ContactPersonForm(ModelForm):
    class Meta:
        model = Contact
        fields = ('person_name', 'organization_name', 'address_street', 'address_city', 'address_province',
                  'address_postal_code', 'address_country', 'contact_voice', 'contact_fax', 'contact_email')


class DomainAddForm(ModelForm):
    class Meta:
        model = Domain
        fields = ('contact_admin', 'contact_billing', 'contact_tech', 'nameserver1', 'nameserver2', 'nameserver3',
                  'nameserver4')

    def __init__(self, current_user, *args, **kwargs):
        super(DomainAddForm, self).__init__(*args, **kwargs)
        self.fields['contact_admin'].queryset = self.fields['contact_admin'].queryset.filter(owner=current_user.id)
        self.fields['contact_billing'].queryset = self.fields['contact_billing'].queryset.filter(owner=current_user.id)
        self.fields['contact_tech'].queryset = self.fields['contact_tech'].queryset.filter(owner=current_user.id)


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
