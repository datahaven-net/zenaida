from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy

from logs.models import RequestLog


class HasExceptionListFilter(admin.SimpleListFilter):

    title = gettext_lazy('have exception')
    parameter_name = 'has_exception'

    def lookups(self, request, model_admin):
        return (
            ('yes', gettext_lazy('Has exception')),
            ('no', gettext_lazy("Doesn't have exception")),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(exception__isnull=False)
        if self.value() == 'no':
            return queryset.filter(exception__isnull=True)


class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'ip_address', 'user', 'method', 'path', 'path_full', 'status_code', 'duration', 'no_exception')
    list_filter = ('timestamp', 'method', 'path', 'status_code', HasExceptionListFilter)
    search_fields = ('timestamp', 'ip_address', 'user', 'method', 'path', 'status_code', 'exception')
    readonly_fields = ('timestamp', 'ip_address', 'user', 'method', 'path', 'path_full', 'status_code', 'duration', 'get_request', 'exception')
    exclude = ('request', )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request, **kwargs):
        return False

    def no_exception(self, obj):
        return not bool(obj.exception)
    no_exception.boolean = True

    def get_request(self, instance):
        return format_html('<pre>{request}</pre>', request=instance.request)
    get_request.short_description = 'Request'

admin.site.register(RequestLog, RequestLogAdmin)
