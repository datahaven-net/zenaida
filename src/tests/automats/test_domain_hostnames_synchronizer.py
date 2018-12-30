import os
import pytest
import datetime

from django.conf import settings
from django.utils.timezone import make_aware

from automats import domain_hostnames_synchronizer

from back import users
from back import contacts
from back import domains

from zepp import zclient


def _prepare_tester_domain(nameservers=[]):
    tester = users.find_account('tester@zenaida.ai')
    if not tester:
        tester = users.create_account('tester@zenaida.ai', account_password='tester', is_active=True, )
    tester_domain = tester.domains.first()
    if not tester_domain:
        tester_registrant = contacts.create(
            epp_id=None,
            owner=tester,
            person_name='Tester Tester Registrant',
            organization_name='TestingCorp',
            address_street='TestStreet',
            address_city='TestCity',
            address_province='TestProvince',
            address_postal_code='TestPostalCode',
            address_country='TestCountry',
            contact_voice='1234567890',
            contact_fax='1234567890',
            contact_email='tester@zenaida.ai',
        )
        tester_contact_admin = contacts.create(
            epp_id=None,
            owner=tester,
            person_name='Tester Tester Admin',
            organization_name='TestingCorp',
            address_street='TestStreet',
            address_city='TestCity',
            address_province='TestProvince',
            address_postal_code='TestPostalCode',
            address_country='TestCountry',
            contact_voice='1234567890',
            contact_fax='1234567890',
            contact_email='tester@zenaida.ai',
        )
        tester_domain = domains.create(
            domain_name='test.%s' % settings.SUPPORTED_ZONES[0],
            owner=tester,
            expiry_date=make_aware(datetime.datetime.now() + datetime.timedelta(days=365)),
            create_date=make_aware(datetime.datetime.now()),
            epp_id=zclient.make_epp_id(tester.email),
            registrar=None,
            registrant=tester_registrant,
            contact_admin=tester_contact_admin,
            nameservers=nameservers,
        )
    return tester_domain


@pytest.mark.django_db
def test_update_hostnames():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = _prepare_tester_domain(nameservers=[
        'ns1.google.com',
        'ns2.google.com',
        'ns3.google.com',
    ])
    scenario1 = []
    cs1 = domain_hostnames_synchronizer.DomainHostnamesSynchronizer(
        update_domain=True,
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs1.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario1.append(
            (oldstate, newstate, event, )
        ),
    )
    cs1.event('run', target_domain=tester_domain, known_domain_info=zclient.cmd_domain_info(domain=tester_domain.name), )
    del cs1
    
    tester_domain.nameserver4 = 'ns4.google.com'
    tester_domain.save()
    scenario2 = []
    cs2 = domain_hostnames_synchronizer.DomainHostnamesSynchronizer(
        update_domain=True,
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs2.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario2.append(
            (oldstate, newstate, event, )
        ),
    )
    cs2.event('run', target_domain=tester_domain, known_domain_info=zclient.cmd_domain_info(domain=tester_domain.name), )
    del cs2
    
    # one nameserver should be removed
    assert scenario1 == [
        ('AT_STARTUP', 'DOMAIN_INFO?', 'run'),
        ('DOMAIN_INFO?', 'HOSTS_CHECK', 'response'),
        ('HOSTS_CHECK', 'DOMAIN_UPDATE!', 'no-hosts-to-be-added'),
        ('DOMAIN_UPDATE!', 'DONE', 'response'),
    ]
    # one nameserver should be added back
    assert scenario2 == [
        ('AT_STARTUP', 'DOMAIN_INFO?', 'run'),
        ('DOMAIN_INFO?', 'HOSTS_CHECK', 'response'),
        ('HOSTS_CHECK', 'HOSTS_CREATE', 'response'),
        ('HOSTS_CREATE', 'DOMAIN_UPDATE!', 'all-hosts-created'),
        ('DOMAIN_UPDATE!', 'DONE', 'response'),
    ]
