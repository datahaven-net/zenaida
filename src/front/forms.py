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
                  'address_postal_code', 'address_country', 'contact_voice', 'contact_fax', 'contact_email', )

    def __init__(self, *args, **kwargs):
        super(ContactPersonForm, self).__init__(*args, **kwargs)
        for field_name in self.fields.keys():
            if field_name not in ['contact_fax', 'address_province', ]:
                self.fields[field_name].required = True


class DomainDetailsForm(ModelForm):
    class Meta:
        model = Domain
        fields = ('contact_admin', 'contact_billing', 'contact_tech',
                  'nameserver1', 'nameserver2', 'nameserver3', 'nameserver4', )

    def __init__(self, current_user, *args, **kwargs):
        super(DomainDetailsForm, self).__init__(*args, **kwargs)
        self.fields['contact_admin'].queryset = self.fields['contact_admin'].queryset.filter(owner=current_user.id)
        self.fields['contact_admin'].label_from_instance = lambda c: c.label
        self.fields['contact_admin'].empty_label = ' ' 
        self.fields['contact_billing'].queryset = self.fields['contact_billing'].queryset.filter(owner=current_user.id)
        self.fields['contact_billing'].label_from_instance = lambda c: c.label
        self.fields['contact_billing'].empty_label = ' ' 
        self.fields['contact_tech'].queryset = self.fields['contact_tech'].queryset.filter(owner=current_user.id)
        self.fields['contact_tech'].label_from_instance = lambda c: c.label
        self.fields['contact_tech'].empty_label = ' ' 

    def clean(self):
        cleaned_data = super(DomainDetailsForm, self).clean()
        contact_admin = cleaned_data.get('contact_admin')
        contact_billing = cleaned_data.get('contact_billing')
        contact_tech = cleaned_data.get('contact_tech')
        if not any([contact_admin, contact_billing, contact_tech, ]):
            raise forms.ValidationError('At least one Contact Person must be specified for the domain.')
        nameserver1 = cleaned_data.get('nameserver1')
        nameserver2 = cleaned_data.get('nameserver2')
        nameserver3 = cleaned_data.get('nameserver3')
        nameserver4 = cleaned_data.get('nameserver4')
        if not any([nameserver1, nameserver2, nameserver3, nameserver4, ]):
            raise forms.ValidationError('At least one Name Server must be specified for the domain.')
        return cleaned_data


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

    def __init__(self, *args, **kwargs):
        super(AccountProfileForm, self).__init__(*args, **kwargs)
        for field_name in self.fields.keys():
            if field_name not in ['contact_fax', 'address_province', ]:
                self.fields[field_name].required = True
