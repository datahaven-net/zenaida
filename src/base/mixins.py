from django import shortcuts
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


class StaffRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'You do not have the permission required to perform the requested operation.')
            return shortcuts.redirect('index')
        return super().dispatch(request, *args, **kwargs)
