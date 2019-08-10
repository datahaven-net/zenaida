import os

from django.forms import forms, models, ModelForm
from back.models.profile import Profile
from back.models.domain import Contact, Domain


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
        ns_list = [
            cleaned_data.get('nameserver1'),
            cleaned_data.get('nameserver2'),
            cleaned_data.get('nameserver3'),
            cleaned_data.get('nameserver4'),
        ]
        if not any(ns_list):
            raise forms.ValidationError('At least one Name Server must be specified for the domain.')
        filled_ns_list = list(filter(None, ns_list))
        if len(filled_ns_list) != len(set(filled_ns_list)):
            raise forms.ValidationError('Name Servers can not be duplicated.')
        invalid_ns_list = []
        for ns in filled_ns_list:
            if not os.system("ping -c 1 " + ns) == 0:
                invalid_ns_list.append(ns)
        if invalid_ns_list:
            raise forms.ValidationError(f"Invalid nameserver(s): {', '.join(map(str, invalid_ns_list))}")
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
        self.fields['contact_email'].disabled = True
        for field_name in self.fields.keys():
            if field_name not in ['contact_fax', 'address_province', ]:
                self.fields[field_name].required = True
