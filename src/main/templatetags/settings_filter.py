from django import template
from django.conf import settings


register = template.Library()


@register.tag
def settings_value(parser, token):
    try:
        tag_name, var = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    return ValueFromSettings(var)


class ValueFromSettings(template.Node):
    def __init__(self, var):
        self.arg = template.Variable(var)
    def render(self, context):
        return settings.__getattr__(str(self.arg))
