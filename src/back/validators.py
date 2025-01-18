from django.core.validators import RegexValidator
from django.db import models

from back.constants import COUNTRIES

phone_regex = RegexValidator(
    regex=r'^\+[0-9]{1,3}\.?[0-9]{1,14}$',
    message="Phone number must be entered in the format: '+123.4567890'. The number must include the country code, which is separated from the phone number (up to 14 digits allowed) by a period."
)


class CountryField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 2)
        kwargs.setdefault('choices', COUNTRIES)

        super(CountryField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"
