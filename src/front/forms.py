import os
import re

from django.conf import settings
from django.forms import forms, models, fields
from back.models.profile import Profile
from back.models.domain import Contact, Domain


class ContactPersonForm(models.ModelForm):

    class Meta:
        model = Contact
        fields = ('person_name', 'organization_name', 'address_street', 'address_city', 'address_province',
                  'address_postal_code', 'address_country', 'contact_voice', 'contact_fax', 'contact_email', )


class DomainDetailsForm(models.ModelForm):

    class Meta:
        model = Domain
        fields = ('contact_admin', 'contact_billing', 'contact_tech',
                  'nameserver1', 'nameserver2', 'nameserver3', 'nameserver4', 'auto_renew_enabled', )

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
            raise forms.ValidationError('At least one nameserver must be specified for the domain.')
        for nameserver in ns_list:
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", nameserver):
                raise forms.ValidationError('Nameserver can not be an IP address.')

        filled_ns_list = list(filter(None, ns_list))
        if len(filled_ns_list) != len(set(filled_ns_list)):
            raise forms.ValidationError('Nameservers can not be duplicated.')
        if settings.ZENAIDA_PING_NAMESERVERS_ENABLED:
            for ns in filled_ns_list:
                if not os.system("ping -c 1 " + ns) == 0:
                    cleaned_data['invalid_nameservers'] = True
                    break
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
            'email_notifications_enabled',
            'automatic_renewal_enabled',
        )

    def __init__(self, *args, **kwargs):
        super(AccountProfileForm, self).__init__(*args, **kwargs)
        self.fields['contact_email'].disabled = True


class DomainLookupForm(forms.Form):

    domain_name = fields.CharField()


class DomainTransferTakeoverForm(forms.Form):
    
    domain_name = fields.CharField()
    transfer_code = fields.CharField()
