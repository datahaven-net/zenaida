from datetime import datetime, timezone

from django.contrib.auth import login, authenticate, REDIRECT_FIELD_NAME
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import SuccessURLAllowedHostsMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.utils.http import is_safe_url
from django.views.generic import RedirectView
from django.views.generic.edit import FormView
from django.conf import settings

from accounts.decorators import check_recaptcha
from accounts.forms import SignInViaEmailForm
from accounts.forms import SignUpForm
from accounts.models.activation import Activation

from zen.zusers import create_profile


class SignInView(SuccessURLAllowedHostsMixin, FormView):
    template_name = 'accounts/login.html'
    if hasattr(settings, 'LOGIN_VIA_EMAIL') and settings.LOGIN_VIA_EMAIL:
        form_class = SignInViaEmailForm
    else:
        form_class = AuthenticationForm

    redirect_field_name = REDIRECT_FIELD_NAME
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super(SignInView, self).get_context_data(**kwargs)
        context['recaptcha_site_key'] = settings.GOOGLE_RECAPTCHA_SITE_KEY
        return context

    def get_success_url(self):
        url = self.get_redirect_url()
        return url or resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_redirect_url(self):
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, '')
        )
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    @check_recaptcha
    def form_valid(self, form):
        if self.request.recaptcha_is_valid or not settings.GOOGLE_RECAPTCHA_SITE_KEY:
            login(self.request, form.get_user())
            messages.add_message(self.request, messages.SUCCESS, 'Successfully logged in!')
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class SignUpView(FormView):
    template_name = 'accounts/register.html'
    form_class = SignUpForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super(SignUpView, self).get_context_data(**kwargs)
        context['recaptcha_site_key'] = settings.GOOGLE_RECAPTCHA_SITE_KEY
        return context

    @check_recaptcha
    def form_valid(self, form):
        if self.request.recaptcha_is_valid or not settings.GOOGLE_RECAPTCHA_SITE_KEY:
            if settings.ENABLE_USER_ACTIVATION:
                user = form.save(commit=False)
                user.is_active = False
                user.save()

                form.send_activation_email(self.request, user)

                messages.add_message(self.request, messages.SUCCESS,
                                     'You are registered. To activate the account, follow the link sent to the mail.')
            else:
                form.save()

                email = form.cleaned_data.get('email')
                raw_password = form.cleaned_data.get('password1')

                user = authenticate(username=email, password=raw_password)
                login(self.request, user)
                create_profile(user, contact_email=email)

                messages.add_message(self.request, messages.SUCCESS, 'You are successfully registered!')
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class ActivateView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'index'

    def get_redirect_url(self, *args, **kwargs):
        activation_obj = Activation.objects.filter(code=kwargs.get('code')).first()
        if not activation_obj:
            messages.error(self.request, 'Activation code is not correct')
            return super().get_redirect_url()

        # Remove activation code if it's created more than 24 hours ago.
        activation_code_time_passed = datetime.now(timezone.utc) - activation_obj.created_at
        if activation_code_time_passed.total_seconds() > 60 * 60 * 24:
            activation_obj.delete()
            messages.error(self.request, 'Activation code is not valid anymore')
            return super().get_redirect_url()

        # Activate user's profile if it's not already activated.
        user = activation_obj.account

        if user.is_active:
            messages.warning(self.request, 'Your account is already activated')
            return super().get_redirect_url()

        user.is_active = True
        user.save()

        messages.success(self.request, 'You have successfully activated your account')
        login(self.request, user)

        # If user do not have a profile yet need to create it for him.
        try:
            user.profile
        except ObjectDoesNotExist:
            create_profile(user, contact_email=user.email)

        return super().get_redirect_url()
