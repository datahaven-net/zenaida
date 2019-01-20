import datetime
from django import template

register = template.Library()


@register.filter()
def add_days(days):
    return datetime.date.today() + datetime.timedelta(days=days)
