from django import forms

class NewPaymentForm(forms.Form):

    amount = forms.fields.ChoiceField(
        label='Amount',
        required=True,
        choices=(
            ('100', '100$', ),
            ('200', '200$', ),
            ('500', '500$', ),
            ('1000', '1000$', ),
            ('1500', '1500$', ),
            ('2000', '2000$', ),
            ('5000', '5000$', ),
        ),
    )

    payment_method = forms.fields.ChoiceField(
        label='Method',
        required=True,
        choices=(
            ('pay_4csonline', 'Credit Card', ),
            ('pay_bank_transfer_anguilla', 'Bank Transfer', ),
        ),
    )
