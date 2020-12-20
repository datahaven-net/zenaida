from django import forms


class DomainSyncForm(forms.Form):
    domain_name = forms.fields.CharField(label='Domain Name')


class CSVFileSyncForm(forms.Form):
    csv_file = forms.fields.FileField()
    dry_run = forms.fields.BooleanField(initial=True, required=False, help_text='Take no actions, but only report differences')
