from django import forms


class TwoFactorResetForm(forms.Form):
    email = forms.fields.EmailField(label='Email')


class BalanceAdjustmentForm(forms.Form):
    email = forms.fields.EmailField(label='Email')
    amount = forms.fields.IntegerField(label='Amount')
    reason = forms.fields.CharField(label='Reason for balance change')


class DomainSyncForm(forms.Form):
    domain_name = forms.fields.CharField(label='Domain Name')


class CSVFileSyncForm(forms.Form):
    csv_file = forms.fields.FileField()
    dry_run = forms.fields.BooleanField(
        initial=False,
        required=False,
        help_text='Take no actions, but only report differences',
    )


class SendingSingleEmailForm(forms.Form):
    receiver = forms.fields.EmailField(label='Receiver')
    subject = forms.fields.CharField(label='Subject', min_length=1, max_length=255)
    body = forms.fields.CharField(label='Body', widget=forms.widgets.Textarea)


class BulkTransferForm(forms.Form):

    new_owner = forms.fields.EmailField(label='New Owner')
    body = forms.fields.CharField(
        label='List of domains and auth codes, line by line',
        widget=forms.widgets.Textarea,
        help_text='Enter a list of domains and authentication codes above, separated by comma or space on each line. '
                  'You can copy and paste here the entire contents of the text file you already downloaded via the admin console.',
    )
