import os
import pytest

from django.conf import settings

from automats import domain_auth_changer

from zen import zerrors
from zen import zdomains

from tests import testsupport


@pytest.mark.django_db
def test_success():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='test-write-0.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
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
    dac = domain_auth_changer.DomainAuthChanger(
        log_events=True,
        log_transitions=True,
    )
    dac.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    new_auth_info = zdomains.generate_random_auth_info()
    dac.event('run', target_domain=tester_domain, new_auth_info=new_auth_info)
    outputs = list(dac.outputs)
    del dac
    assert scenario == [
        ('AT_STARTUP', 'INFO?', 'run'),
        ('INFO?', 'SET_AUTH!', 'response'),
        ('SET_AUTH!', 'DONE', 'response'),
    ]
    assert len(outputs) == 1
    assert outputs[0]['epp']['response']['result']['@code'] == '1000'
    tester_domain.refresh_from_db()
    assert tester_domain.auth_key == new_auth_info


@pytest.mark.django_db
def test_authorization_error():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='owned-by-another-registar.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
        domain_epp_id='some_epp_id_123',
    )
    scenario = []
    dac = domain_auth_changer.DomainAuthChanger(
        log_events=True,
        log_transitions=True,
    )
    dac.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    new_auth_info = zdomains.generate_random_auth_info()
    dac.event('run', target_domain=tester_domain, new_auth_info=new_auth_info)
    outputs = list(dac.outputs)
    del dac
    assert scenario == [
        ('AT_STARTUP', 'INFO?', 'run'),
        ('INFO?', 'FAILED', 'error'),
    ]
    assert len(outputs) == 1
    assert isinstance(outputs[0], zerrors.EPPAuthorizationError)
