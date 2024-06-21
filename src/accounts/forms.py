import logging

from friendly_captcha.fields import FrcCaptchaField

from django import forms
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from accounts.models.activation import Activation
from accounts.models.account import Account


class FriendlyCaptchaAuthenticationForm(AuthenticationForm):
    captcha = FrcCaptchaField()


class SignInViaEmailForm(forms.Form):

    redirect_field_name = REDIRECT_FIELD_NAME

    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'placeholder': '@', 'focus': True}),
    )
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput,
    )
    if hasattr(settings, 'FRC_CAPTCHA_SECRET') and settings.FRC_CAPTCHA_SECRET:
        captcha = FrcCaptchaField()

    error_messages = {
        'invalid_login': _(
            'Please enter a correct %(email)s and password. Note that both '
            'fields may be case-sensitive.'
        ),
        'inactive': _('This account is not active yet. You must verify your email before you can login, please follow the link sent to you via email.'),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if email is not None and password:
            email = email.lower()
            self.user_cache = Account.objects.filter(email=email).first()
            if self.user_cache:
                self.confirm_login_allowed(self.user_cache)
                if not self.user_cache.check_password(password):
                    self.invalid_login(email)
            else:
                self.invalid_login(email)
        return self.cleaned_data

    def invalid_login(self, email):
        raise forms.ValidationError(
            self.error_messages['invalid_login'],
            code='invalid_login',
            params={'email': email},
        )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )

    def get_user(self):
        return self.user_cache


class SignUpForm(UserCreationForm):

    class Meta:
        model = Account
        fields = ('email', 'password1', 'password2',)

    email = forms.EmailField(max_length=255, help_text=_('Required. Type a valid email address.'))

    if hasattr(settings, 'FRC_CAPTCHA_SECRET') and settings.FRC_CAPTCHA_SECRET:
        captcha = FrcCaptchaField()

    error_messages = {
        'unique_email': _('You can not use this email.'),
        'password_mismatch': _("The two password fields didn't match."),
    }

    def clean(self):
        email = self.cleaned_data.get('email')
        if email is not None:
            email = email.lower()
            num_users = Account.objects.filter(email=email).count()
            if num_users > 0:
                raise forms.ValidationError(
                    self.error_messages['unique_email'],
                    code='unique_email',
                )
        return self.cleaned_data

    @staticmethod
    def send_activation_email(request, user):
        from_email = settings.DEFAULT_FROM_EMAIL
        domain = Site.objects.get_current().domain
        code = get_random_string(20)
        subject = 'Profile Activation on %s' % domain

        context = {
            'domain': domain,
            'code': code,
        }

        act = Activation()
        act.code = code
        act.account = user
        act.save()

        html_content = render_to_string('email/activation_profile.html', context=context, request=request)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(subject, text_content, from_email,
                                     to=[user.email, ], bcc=[user.email, ], cc=[user.email, ])
        msg.attach_alternative(html_content, 'text/html')
        try:
            msg.send()
        except:
            logging.exception('Failed to send email')


class CustomPasswordResetForm(PasswordResetForm):

    def clean(self):
        if 'email' in self.cleaned_data:
            self.cleaned_data['email'] = self.cleaned_data['email'].lower()
        return self.cleaned_data
