import re
import logging
import time

from django.conf import settings
from django.http import HttpResponse

from redis import Redis

logger = logging.getLogger(__name__)


class HttpResponseRateLimitExceeded(HttpResponse):
    status_code = 429


class RedisClient:

    def __init__(self, client: Redis):
        self.client = client

    def incr(self, key: str):
        return self.client.incr(key)

    def expire(self, key: str, ex: int):
        return self.client.expire(key, ex)


class RateLimiterMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.limit = settings.RATE_LIMIT_COUNT
        self.window = settings.RATE_LIMIT_WINDOW_SECONDS
        self.targets = settings.RATE_LIMIT_TARGET_PATHS
        self.redis_client = RedisClient(client=Redis())

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)

        ip_addr = self.client_ip(request)
        request_path = (request.path or '').rstrip("/")

        # Only use rate limiter for the selected end-points
        if (request.method, request_path.rstrip("/")) not in self.targets:
            return self.get_response(request)

        # Create the cache key using the client's IP and the current minute timestamp
        key = f"{ip_addr}:{int(time.time() // self.window)}"

        # Check the current request count for the client
        request_count = self.redis_client.incr(key)
        if request_count is None:
            # ignore Cache errors
            return self.get_response(request)

        if request_count == 1:
            # Set an expiration for the key if it's the first request within the window
            self.redis_client.expire(key, self.window)

        # Check if the client has exceeded the rate limit
        if request_count > self.limit:
            logger.critical(f"Rate limit exceeded for [{key}]")
            return HttpResponseRateLimitExceeded(content=b'please try again later')

        return self.get_response(request)

    def client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        ip = re.sub(r'[^a-zA-Z0-9\.]', '', ip)
        return ip
