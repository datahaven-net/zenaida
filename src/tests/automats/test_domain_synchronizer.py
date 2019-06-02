import os
import pytest

from django.conf import settings
from django.utils.timezone import now

from automats import domain_synchronizer

from zen import zerrors

from tests import testsupport


@pytest.mark.django_db
def test_domain_another_registrar():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='owned-by-another-registar.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
        domain_epp_id='some_epp_id_123',
    )
    scenario = []
    ds = domain_synchronizer.DomainSynchronizer(
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    ds.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    ds.event('run', tester_domain, update_domain=True)
    outputs = list(ds.outputs)
    del ds
    assert scenario == [
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'OWNER?', 'response'),
        ('OWNER?', 'FAILED', 'response'),
    ]
    assert len(outputs) == 1
    assert isinstance(outputs[0], zerrors.EPPRegistrarAuthFailed)


@pytest.mark.django_db
def test_domain_create():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    if os.environ.get('MANUAL', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='test-%s.%s' % (now().strftime('%Y%m%d%H%M%S'), settings.ZENAIDA_SUPPORTED_ZONES[0]),
    )
    assert tester_domain.epp_id is None
    scenario = []
    ds = domain_synchronizer.DomainSynchronizer(
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    ds.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    ds.event('run', tester_domain, renew_years=2, sync_contacts=True, sync_nameservers=True)
    outputs = list(ds.outputs)
    del ds
    assert scenario == [
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'CONTACTS', 'response'),
        ('CONTACTS', 'NAMESERVERS', 'contacts-ok'),
        ('NAMESERVERS', 'CREATE!', 'nameservers-ok'),
        ('CREATE!', 'READ', 'response'),
        ('READ', 'UPDATE!', 'response'),
        ('UPDATE!', 'DONE', 'no-updates'),
    ]
    assert tester_domain.epp_id is not None
    assert len(outputs) == 7
    assert outputs[-1] is True


@pytest.mark.django_db
def test_domain_no_updates():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='test-write-0.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
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
    ds = domain_synchronizer.DomainSynchronizer(
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    ds.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    ds.event('run', tester_domain, renew_years=None, sync_contacts=True, sync_nameservers=True)
    outputs = list(ds.outputs)
    del ds
    assert scenario == [
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'OWNER?', 'response'),
        ('OWNER?', 'CONTACTS', 'response'),
        ('CONTACTS', 'NAMESERVERS', 'contacts-ok'),
        ('NAMESERVERS', 'READ', 'nameservers-ok'),
        ('READ', 'UPDATE!', 'response'),
        ('UPDATE!', 'DONE', 'no-updates'),
    ]
    assert len(outputs) == 5
    assert outputs[-1] is True
