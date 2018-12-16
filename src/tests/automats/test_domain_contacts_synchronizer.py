import os
import pytest
import datetime

from django.conf import settings
from django.utils.timezone import make_aware

from automats import domain_contacts_synchronizer

from back import users
from back import contacts
from back import domains

from zepp import zclient


def _prepare_tester_domain():
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
        tester_contact_tech = contacts.create(
            epp_id=None,
            owner=tester,
            person_name='Tester Tester Tech',
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
        tester_contact_billing = contacts.create(
            epp_id=None,
            owner=tester,
            person_name='Tester Tester Billing',
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
            contact_tech=tester_contact_tech,
            contact_billing=tester_contact_billing,
            nameservers=[
                'ns1.google.com',
                'ns2.google.com',
                'ns3.google.com',
                'ns4.google.com',
            ],
        )
    return tester_domain


@pytest.mark.django_db
def test_domain_update():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')
    tester_domain = _prepare_tester_domain()
    scenario = []
    cs = domain_contacts_synchronizer.DomainContactsSynchronizer(
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    cs.event('run', tester_domain, update_domain=True)
    del cs
    assert scenario == [
        ('AT_STARTUP', 'SYNC_CONTACTS', 'run'),
        ('SYNC_CONTACTS', 'DOMAIN_INFO?', 'all-contacts-in-sync'),
        ('DOMAIN_INFO?', 'DOMAIN_UPDATE', 'response'),
        ('DOMAIN_UPDATE', 'DONE', 'response'),
    ]
