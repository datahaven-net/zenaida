from django import forms


class BalanceAdjustmentForm(forms.Form):
    email = forms.fields.EmailField(label='Email')
    amount = forms.fields.IntegerField(label='Amount')
    reason = forms.fields.CharField(label='Reason for balance change')


class DomainSyncForm(forms.Form):
    domain_name = forms.fields.CharField(label='Domain Name')


class CSVFileSyncForm(forms.Form):
    csv_file = forms.fields.FileField()
    dry_run = forms.fields.BooleanField(
        initial=True, required=False, help_text='Take no actions, but only report differences'
    )
