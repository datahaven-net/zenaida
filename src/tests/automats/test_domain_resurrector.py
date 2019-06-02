import os
import pytest

from django.conf import settings

from automats import domain_resurrector

from zen import zmaster
from zen import zdomains
from zen import zerrors

from tests import testsupport


@pytest.mark.django_db
def test_domain_pending_delete_status_not_set():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    if os.environ.get('MANUAL', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable

    # first need to read existing domain from back-end and create it in local DB
    testsupport.prepare_tester_registrant(epp_id='tester087401xo2c', create_new=True)
    zmaster.domain_synchronize_from_backend(
        'test-restore-0.ai',
        refresh_contacts=True,
        change_owner_allowed=False,
        soft_delete=False,
    )
    tester_domain = zdomains.domain_find(domain_name='test-restore-0.ai')
    assert tester_domain.epp_id is not None

    # now try to restore it
    scenario = []
    ds = domain_resurrector.DomainResurrector(
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    ds.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    ds.event('run', domain_object=tester_domain)
    outputs = list(ds.outputs)
    del ds
    
    # this domain is not possible to restore because status is not pending delete 
    assert scenario == [
        ('AT_STARTUP', 'VERIFY?', 'run'),
        ('VERIFY?', 'RESTORE!', 'verify-ok'),
        ('RESTORE!', 'FAILED', 'error'),
    ]
    assert tester_domain.epp_id is not None
    assert len(outputs) == 5
    assert isinstance(outputs[-1], Exception) 


@pytest.mark.django_db
def test_domain_restore():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    if os.environ.get('MANUAL', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable

    # first need to read existing domain from back-end and create it in local DB
    testsupport.prepare_tester_registrant(epp_id='tester087401xo2c', create_new=True)
    zmaster.domain_synchronize_from_backend(
        'test-restore-1.ai',
        refresh_contacts=True,
        change_owner_allowed=False,
        soft_delete=False,
    )
    tester_domain = zdomains.domain_find(domain_name='test-restore-1.ai')
    assert tester_domain.epp_id is not None
    
    # TODO: ...
