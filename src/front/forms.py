import os
import re

from django.conf import settings
from django.forms import forms, models, fields
from django.utils.safestring import mark_safe

from back.models.profile import Profile
from back.models.domain import Contact, Domain


def encode_ascii_for_list_of_strings(values):
    for value in values:
        if isinstance(value, str):
            try:
                value.encode('ascii')
            except UnicodeEncodeError:
                raise forms.ValidationError('Please use only English characters in your details.')
    return


class ContactPersonForm(models.ModelForm):

    class Meta:
        model = Contact
        fields = ('person_name', 'organization_name', 'address_street', 'address_city', 'address_province',
                  'address_postal_code', 'address_country', 'contact_voice', 'contact_fax', 'contact_email', )

    def clean(self):
        cleaned_data = super(ContactPersonForm, self).clean()
        encode_ascii_for_list_of_strings(cleaned_data.values())
        return cleaned_data


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

    def clean_ns(self, v):
        return v.lower().replace('http:', '').replace('https:', '').strip('.').strip('/')

    def clean(self):
        cleaned_data = super(DomainDetailsForm, self).clean()
        cleaned_data['nameserver1'] = self.clean_ns(cleaned_data.get('nameserver1', ''))
        cleaned_data['nameserver2'] = self.clean_ns(cleaned_data.get('nameserver2', ''))
        cleaned_data['nameserver3'] = self.clean_ns(cleaned_data.get('nameserver3', ''))
        cleaned_data['nameserver4'] = self.clean_ns(cleaned_data.get('nameserver4', ''))
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
                raise forms.ValidationError('Please use DNS name instead of IP address for the nameservers.')
            if self.instance.name and nameserver.endswith(self.instance.name.strip().lower()):
                raise forms.ValidationError(f'Please use another nameserver instead of {nameserver}, "glue" records are not supported yet.')

        filled_ns_list = list(filter(None, ns_list))
        if len(filled_ns_list) != len(set(filled_ns_list)):
            raise forms.ValidationError('Found duplicated nameservers.')

        invalid_nameservers = []
        if settings.ZENAIDA_PING_NAMESERVERS_ENABLED:
            for ns in filled_ns_list:
                if not os.system("ping -c 1 " + ns) == 0:
                    invalid_nameservers.append(ns)

        if invalid_nameservers:
            invalid_nameservers = ', '.join(invalid_nameservers)
            raise forms.ValidationError(
                mark_safe(
                    f"List of nameservers that are not valid or not reachable at this moment: <br>"
                    f"{invalid_nameservers} <br>"
                    f"Please try again later or specify valid and available nameservers."
                )
            )

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

    def clean(self):
        cleaned_data = super(AccountProfileForm, self).clean()
        encode_ascii_for_list_of_strings(cleaned_data.values())
        return cleaned_data


class DomainLookupForm(forms.Form):

    domain_name = fields.CharField()


class DomainTransferTakeoverForm(forms.Form):

    domain_name = fields.CharField()
    transfer_code = fields.CharField()
