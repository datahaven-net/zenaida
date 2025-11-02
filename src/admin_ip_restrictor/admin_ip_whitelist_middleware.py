import ipaddress
import logging

try:
    from ipware.ip2 import get_client_ip
except ImportError:
    from ipware.ip import get_client_ip

from django.conf import settings
from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class AdminIPRestrictorMiddleware(MiddlewareMixin):

    def __init__(self, get_response=None):
        self.get_response = get_response
        restrict_admin = getattr(settings, 'RESTRICT_ADMIN', False)
        trust_private_ip = getattr(settings, 'TRUST_PRIVATE_IP', False)
        self.trust_private_ip = self.parse_bool_envars(trust_private_ip)
        self.restrict_admin = self.parse_bool_envars(restrict_admin)
        allowed_admin_ips = getattr(settings, 'ALLOWED_ADMIN_IPS', [])
        self.allowed_admin_ips = self.parse_list_envars(allowed_admin_ips)
        allowed_admin_ip_ranges = getattr(settings, 'ALLOWED_ADMIN_IP_RANGES', [])
        self.allowed_admin_ip_ranges = self.parse_list_envars(allowed_admin_ip_ranges)
        restricted_app_names = getattr(settings, 'RESTRICTED_APP_NAMES', [])
        self.restricted_app_names = self.parse_list_envars(restricted_app_names)
        self.restricted_app_names.append('admin')

    @staticmethod
    def parse_bool_envars(value):
        if value in ('true', 'True', '1', 1):
            return True
        return False

    @staticmethod
    def parse_list_envars(value):
        if type(value) == list:
            return value
        else:
            return value.split(',')

    def is_blocked(self, ip):
        """Determine if an IP address should be considered blocked."""
        blocked = True

        if self.trust_private_ip:
            if ipaddress.ip_address(ip).is_private:
                blocked = False

        if ip in self.allowed_admin_ips:
            blocked = False

        for allowed_range in self.allowed_admin_ip_ranges:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(allowed_range):
                blocked = False

        return blocked

    def get_ip(self, request):
        client_ip, is_routable = get_client_ip(request)
        assert client_ip, 'IP not found'
        if not self.trust_private_ip:
            assert is_routable, 'IP is private'
        return client_ip

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            app_name = request.resolver_match.app_name
            is_restricted_app = app_name in self.restricted_app_names
            if self.restrict_admin and is_restricted_app:
                ip = self.get_ip(request)
                if self.is_blocked(ip):
                    logger.critical(f"Admin access was blocked from [{ip}]")
                    raise Http404()
        except Exception as exc:
            logger.exception(str(exc))

        return None
