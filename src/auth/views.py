from django.contrib.auth.mixins import LoginRequiredMixin


class BaseLoginRequiredMixin(LoginRequiredMixin):
    login_url = '/accounts/login/'
    permission_denied_message = 'You are not authorized.'
