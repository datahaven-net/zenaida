import logging
import time
import traceback

from logs.models import RequestLog


logger = logging.getLogger(__name__)


class LogRequestsMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._start_time = time.monotonic_ns()
        request_body = self.request_body(request)
        response = self.get_response(request)
        if response.streaming:
            return response
        if not self.log_filter(request):
            return response
        try:
            RequestLog.objects.create(
                ip_address=self.client_ip(request),
                user=self.user_email(request),
                method=request.method,
                path=request.path,
                request=request_body,
                status_code=response.status_code,
                exception=getattr(request, '_captured_exception', None) or None,
                duration=(time.monotonic_ns() - request._start_time) / 1000000000.0,
            )
        except:
            logger.exception("Failed to create APILog record")
        return response

    def process_exception(self, request, exception):
        request._captured_exception = str(exception) + '\n\n' + traceback.format_exc()
        return None

    def log_filter(self, request):
        if self.client_ip(request) == '45.76.43.120':
            # skip logging all monitoring requests from specific host
            return False
        p = request.path
        if p in [
            '/favicon.ico',
            '/robots.txt',
        ]:
            # skip logging of some specific requests
            return False
        if p.count('/admin/') or p.count('/_nested_admin'):
            # skip logging of admin requests
            return False
        return True

    def user_email(self, request):
        u = getattr(request, 'user', '')
        if u:
            if getattr(u, 'email', ''):
                return u.email
        return u

    def client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def request_body(self, request):
        raw_request_body = ""
        if request.POST:
            try:
                raw_request_body += '\n'.join(['%s=%s' % (k, v) for k, v in request.POST.items() if k not in [
                    'csrfmiddlewaretoken', 'auth-password', 'g-recaptcha-response',
                ]])
            except Exception as e:
                raw_request_body += str(e)
        if request.GET:
            if raw_request_body:
                raw_request_body += '\n'
            try:
                raw_request_body += '\n'.join(['%s=%s' % (k, v) for k, v in request.GET.items()])
            except Exception as e:
                raw_request_body += str(e)
        return raw_request_body
