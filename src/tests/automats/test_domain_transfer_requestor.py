import os
import pytest

from django.conf import settings

from automats import domain_transfer_requestor

from epp import rpc_error

from zen import zdomains

from tests import testsupport


@pytest.mark.django_db
def test_domain_not_exist():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dtr = domain_transfer_requestor.DomainTransferRequestor(
        log_events=True,
        log_transitions=True,
    )
    dtr.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    new_auth_info = zdomains.generate_random_auth_info()
    dtr.event('run', target_domain_name='this-domain-not-exist.ai', auth_info=new_auth_info)
    outputs = list(dtr.outputs)
    del dtr
    assert scenario == [
        ('AT_STARTUP', 'DOMAIN_INFO', 'run'),
        ('DOMAIN_INFO', 'FAIL', 'response'),
    ]
    assert len(outputs) == 1
    assert outputs[0]
    assert isinstance(outputs[0], rpc_error.EPPUnexpectedResponse)


@pytest.mark.django_db
def test_domain_same_registrar():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dtr = domain_transfer_requestor.DomainTransferRequestor(
        log_events=True,
        log_transitions=True,
    )
    dtr.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    dtr.event('run', target_domain_name='test-transfer-request.ai', auth_info='abc123')
    outputs = list(dtr.outputs)
    del dtr
    assert scenario == [
        ('AT_STARTUP', 'DOMAIN_INFO', 'run'),
        ('DOMAIN_INFO', 'FAIL', 'response'),
    ]
    assert len(outputs) == 1
    assert outputs[0]
    assert isinstance(outputs[0], rpc_error.EPPRegistrarAuthFailed)


@pytest.mark.django_db
def test_transfer_request_sent():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dtr = domain_transfer_requestor.DomainTransferRequestor(
        skip_info=False,
        auth_info_verify=False,
        log_events=True,
        log_transitions=True,
    )
    dtr.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    dtr.event('run', target_domain_name='can-not-be-transferred.ai', auth_info='abc123')
    outputs = list(dtr.outputs)
    del dtr
    assert scenario == [
        ('AT_STARTUP', 'DOMAIN_INFO', 'run'),
        ('DOMAIN_INFO', 'FAIL', 'response'),
    ]
    assert len(outputs) == 1
    assert outputs[0]
    assert isinstance(outputs[0], rpc_error.EPPRegistrarAuthFailed)
