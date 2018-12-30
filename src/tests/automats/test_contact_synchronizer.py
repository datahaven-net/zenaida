import os
import time
import pytest

from automats import contact_synchronizer

from back import users
from back import contacts

from zepp import zclient


def _prepare_tester_contact():
    tester = users.find_account('tester@zenaida.ai')
    if not tester:
        tester = users.create_account('tester@zenaida.ai', account_password='tester', is_active=True, )
    tester_contact = tester.contacts.first()
    if not tester_contact:
        tester_contact = contacts.create(
            epp_id=None,
            owner=tester,
            person_name='Tester Tester',
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
    return tester_contact


@pytest.mark.django_db
def test_contact_create():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')
    tester_contact = _prepare_tester_contact()
    scenario = []
    cs = contact_synchronizer.ContactSynchronizer(
        log_events=True,
        log_transitions=True,
    )
    cs.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    cs.event('run', tester_contact)
    del cs
    assert tester_contact.epp_id != ''
    delete_response = zclient.cmd_contact_delete(tester_contact.epp_id)
    assert delete_response['epp']['response']['result']['@code'] == '1000'
    tester_contact.epp_id = None
    tester_contact.save()
    assert scenario == [
        ('AT_STARTUP', 'CONTACT_CREATE', 'run'),
        ('CONTACT_CREATE', 'DONE', 'response'),
    ]


@pytest.mark.django_db
def test_contact_recreate():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')
    tester_contact = _prepare_tester_contact()
    tester_contact.epp_id = 'not_exising_epp_id'
    tester_contact.person_name = 'Tester Tester ' + str(int(time.time()))
    tester_contact.save()
    scenario = []
    cs = contact_synchronizer.ContactSynchronizer(
        log_events=True,
        log_transitions=True,
    )
    cs.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    cs.event('run', tester_contact)
    del cs
    assert tester_contact.epp_id != ''
    delete_response = zclient.cmd_contact_delete(tester_contact.epp_id)
    assert delete_response['epp']['response']['result']['@code'] == '1000'
    tester_contact.epp_id = None
    tester_contact.save()
    assert scenario == [
        ('AT_STARTUP', 'CONTACT_UPDATE', 'run'),
        ('CONTACT_UPDATE', 'CONTACT_RECREATE', 'response'),
        ('CONTACT_RECREATE', 'DONE', 'response'),
    ]


@pytest.mark.django_db
def test_contact_update():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')
    tester_contact = _prepare_tester_contact()
    existing_contact_id = zclient.make_epp_id(tester_contact.contact_email)
    existing_contact_info = contacts.to_dict(tester_contact)
    create_response = zclient.cmd_contact_create(
        contact_id=existing_contact_id,
        email=existing_contact_info['email'],
        voice=existing_contact_info['voice'],
        fax=existing_contact_info['fax'],
        # auth_info=auth_info,
        contacts_list=existing_contact_info['contacts'],
        raise_for_result=False,
    )
    assert create_response['epp']['response']['result']['@code'] == '1000'
    tester_contact.epp_id = existing_contact_id
    tester_contact.person_name = 'Tester Tester ' + str(int(time.time()))
    tester_contact.save()
    scenario = []
    cs = contact_synchronizer.ContactSynchronizer(
        log_events=True,
        log_transitions=True,
    )
    cs.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    cs.event('run', tester_contact)
    del cs
    assert tester_contact.epp_id != ''
    delete_response = zclient.cmd_contact_delete(tester_contact.epp_id)
    assert delete_response['epp']['response']['result']['@code'] == '1000'
    tester_contact.epp_id = None
    tester_contact.save()
    assert scenario == [
        ('AT_STARTUP', 'CONTACT_UPDATE', 'run'),
        ('CONTACT_UPDATE', 'DONE', 'response'),
    ]
