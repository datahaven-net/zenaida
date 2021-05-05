import logging

from back.models.zone import Zone

from django.conf import settings

logger = logging.getLogger(__name__)


def is_supported(tld_zone_name):
    """
    Return `True` if given zone is supported by this Zenaida host.
    """
    return tld_zone_name in settings.ZENAIDA_SUPPORTED_ZONES


def is_exist(tld_zone_name):
    """
    Return `True` if such zone exists, doing query in Zone table.
    """
    return bool(Zone.zones.filter(name=tld_zone_name).first())


def make(tld_zone_name):
    """
    Creates new zone with given tld name if it not exists, otherwise returns existing object.
    """
    if not is_supported(tld_zone_name):
        raise ValueError('Zone "%s" is not supported by the server' % tld_zone_name)
    zon_obj = Zone.zones.filter(name=tld_zone_name).first()
    if not zon_obj:
        zon_obj = Zone(name=tld_zone_name)
        zon_obj.save()
        logger.info('new zone created: %r', zon_obj)
    return zon_obj
