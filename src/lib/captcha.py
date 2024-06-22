from captcha.fields import CaptchaField as OriginalCaptchaField
from captcha.models import CaptchaStore
from captcha.conf import settings

from django.forms import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy


class CaptchaField(OriginalCaptchaField):

    def clean(self, value):
        super(OriginalCaptchaField, self).clean(value)
        response, value[1] = (value[1] or "").strip().lower(), ""
        if not settings.CAPTCHA_GET_FROM_POOL:
            CaptchaStore.remove_expired()
        if settings.CAPTCHA_TEST_MODE and response.lower() == "passed":
            # automatically pass the test
            try:
                # try to delete the captcha based on its hash
                CaptchaStore.objects.get(hashkey=value[0]).delete()
            except CaptchaStore.DoesNotExist:
                # ignore errors
                pass
        elif not self.required and not response:
            pass
        else:
            try:
                CaptchaStore.objects.get(
                    response=response, hashkey=value[0], expiration__gt=timezone.now()
                )
            except CaptchaStore.DoesNotExist:
                raise ValidationError(
                    getattr(self, "error_messages", {}).get(
                        "invalid", gettext_lazy("Invalid CAPTCHA")
                    )
                )
        return value
