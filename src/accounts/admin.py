from django.contrib import admin
from nested_admin import NestedModelAdmin

from accounts.models import Activation


class ActivationAdmin(NestedModelAdmin):
    pass


admin.site.register(Activation, ActivationAdmin)
