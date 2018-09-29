from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm

from accounts.forms import SignInViaEmailForm


def get_login_form():
    if hasattr(settings, 'LOGIN_VIA_EMAIL') and settings.LOGIN_VIA_EMAIL:
        return SignInViaEmailForm

    return AuthenticationForm


def email_send(receiver, subject, message, email_from, ):
    recipient_list = [receiver,]
    send_mail(subject, message, email_from, recipient_list)
    return True
