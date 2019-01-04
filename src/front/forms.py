from django.forms import forms, fields, models, ModelForm, TextInput
from back.models.profile import Profile
from back.models.domain import Domain


class DomainLookupForm(forms.Form):
    domain_name = fields.CharField(label='', max_length=100, required=True,
                                   widget=TextInput(attrs={'placeholder': 'Find your domain'}),)


class DomainCreateForm(forms.Form):
    domain_name = fields.CharField(label='Domain Name', max_length=100, required=True)


class ContactForm(forms.Form):
    # TODO Instead of forms, use ModelForm
    person_name = fields.CharField(label='Contact Person Name', max_length=255)
    organization_name = fields.CharField(label='Name of Organization', max_length=255)
    address_street = fields.CharField(label='Street Name', max_length=255)
    address_city = fields.CharField(label='City', max_length=255)
    address_province = fields.CharField(label='Province', max_length=255)
    address_postal_code = fields.CharField(label='Postcode', max_length=255)
    address_country = fields.CharField(label='Country', max_length=255)
    contact_voice = fields.CharField(label='Phone Number', max_length=255)
    contact_fax = fields.CharField(label='Fax_number', max_length=255)
    contact_email = fields.EmailField(max_length=255)


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
