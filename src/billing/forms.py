import datetime

from django import forms
from django.conf import settings


class NewPaymentForm(forms.Form):

    amount = forms.fields.IntegerField(
        label='Amount to pay',
        max_value=int(50 * settings.ZENAIDA_DOMAIN_PRICE),
        min_value=int(settings.ZENAIDA_DOMAIN_PRICE),
    )

    @staticmethod
    def _get_payment_method_choices():
        payment_method_choices = []
        if settings.ZENAIDA_BILLING_4CSONLINE_ENABLED:
            payment_method_choices.append(('pay_4csonline', 'Credit Card'))
        if settings.ZENAIDA_BILLING_BTCPAY_ENABLED:
            payment_method_choices.append(('pay_btcpay', 'BitCoin'))
        return tuple(payment_method_choices)

    payment_method = forms.fields.ChoiceField(
        label='Payment method',
        required=True,
        choices=_get_payment_method_choices.__func__,
    )


class FilterOrdersByDateForm(forms.Form):

    @staticmethod
    def _get_year_choices():
        today = datetime.datetime.today()
        year_choices = [(None, '-')]
        for index in range(today.year - 2018):
            year_choices.append((str(2019+index), str(2019+index)))
        return tuple(year_choices)

    year = forms.fields.ChoiceField(
        choices=_get_year_choices.__func__,
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
