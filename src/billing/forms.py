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
        label='Payment Method',
        required=True,
        choices=(
            # ('pay_4csonline', 'Credit Card', ),
            ('pay_btcpay', 'BitCoin'),
        ),
    )


class FilterOrdersByDateForm(forms.Form):
    year = forms.fields.ChoiceField(
        choices=(
            (None, '-'),
            ('2020', '2020',),
            ('2019', '2019',),
        ),
    )
    month = forms.fields.ChoiceField(
        choices=(
            (None, '-'),
            ('1', 'January',),
            ('2', 'February',),
            ('3', 'March',),
            ('4', 'April',),
            ('5', 'May',),
            ('6', 'June',),
            ('7', 'July',),
            ('8', 'August',),
            ('9', 'September',),
            ('10', 'October',),
            ('11', 'November',),
            ('12', 'December',),
        ),
        required=False,
    )
