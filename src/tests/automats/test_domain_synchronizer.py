import os
import pytest
import datetime

from django.conf import settings
from django.utils.timezone import make_aware, now

from automats import domain_synchronizer

from back import users
from back import contacts
from back import domains

from zepp import zclient


def _prepare_tester_domain(domain_name, auth_key='', domain_epp_id=None,
                           add_contacts=['registrant', 'admin', 'billing', 'tech', ],
                           epp_id_dict={},
                           nameservers=['ns1.google.com', 'ns2.google.com', ], ):
    tester = users.find_account('tester@zenaida.ai')
    if not tester:
        tester = users.create_account('tester@zenaida.ai', account_password='tester', is_active=True, )
    tester_registrant = contacts.create(
        epp_id=epp_id_dict.get('registrant'),
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
    ) if 'registrant' in add_contacts else None
    tester_contact_admin = contacts.create(
        epp_id=epp_id_dict.get('admin'),
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
    ) if 'admin' in add_contacts else None
    tester_contact_tech = contacts.create(
        epp_id=epp_id_dict.get('tech'),
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
    ) if 'tech' in add_contacts else None
    tester_contact_billing = contacts.create(
        epp_id=epp_id_dict.get('billing'),
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
    ) if 'billing' in add_contacts else None
    tester_domain = domains.create(
        domain_name=domain_name,
        owner=tester,
        expiry_date=make_aware(datetime.datetime.now() + datetime.timedelta(days=365)),
        create_date=make_aware(datetime.datetime.now()),
        epp_id=domain_epp_id,
        auth_key=auth_key,
        registrar=None,
        registrant=tester_registrant,
        contact_admin=tester_contact_admin,
        contact_tech=tester_contact_tech,
        contact_billing=tester_contact_billing,
        nameservers=nameservers,
    )
    return tester_domain


@pytest.mark.django_db
def test_domain_another_registrar():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = _prepare_tester_domain(
        domain_name='owned-by-another-registar.%s' % settings.SUPPORTED_ZONES[0],
        domain_epp_id='some_epp_id_123',
    )
    scenario = []
    cs = domain_synchronizer.DomainSynchronizer(
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
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'OWNER?', 'response'),
        ('OWNER?', 'FAILED', 'response'),
    ]


@pytest.mark.django_db
def test_domain_create():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = _prepare_tester_domain(
        domain_name='test-%s.%s' % (now().strftime('%Y%m%d%H%M%S'), settings.SUPPORTED_ZONES[0]),
    )
    assert tester_domain.epp_id is None
    scenario = []
    cs = domain_synchronizer.DomainSynchronizer(
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    cs.event('run', tester_domain, renew_years=2, sync_contacts=True, sync_nameservers=True)
    del cs
    assert scenario == [
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'CONTACTS', 'response'),
        ('CONTACTS', 'NAMESERVERS', 'contacts-ok'),
        ('NAMESERVERS', 'CREATE!', 'nameservers-ok'),
        ('CREATE!', 'READ', 'response'),
        ('READ', 'UPDATE!', 'response'),
        ('UPDATE!', 'RENEW', 'no-updates'),
        ('RENEW', 'DONE', 'response'),
    ]
    assert tester_domain.epp_id is not None


@pytest.mark.django_db
def test_domain_no_updates():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = _prepare_tester_domain(
        domain_name='test-write-0.%s' % settings.SUPPORTED_ZONES[0],
        # TODO: take this from CoCCA server, need to prepare test data on the server
        domain_epp_id='86_zenaida',
        epp_id_dict={
            'registrant': 'TestWrite_0',
            'admin': 'TestWrite_0',
            'billing': 'TestWrite_0',
            'tech': 'TestWrite_0',
        },
        nameservers=['ns1.google.com', 'ns2.google.com', ],
    )
    scenario = []
    cs = domain_synchronizer.DomainSynchronizer(
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    cs.event('run', tester_domain, renew_years=None, sync_contacts=True, sync_nameservers=True)
    del cs
    assert scenario == [
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'OWNER?', 'response'),
        ('OWNER?', 'CONTACTS', 'response'),
        ('CONTACTS', 'NAMESERVERS', 'contacts-ok'),
        ('NAMESERVERS', 'READ', 'nameservers-ok'),
        ('READ', 'UPDATE!', 'response'),
        ('UPDATE!', 'DONE', 'no-updates'),
    ]
