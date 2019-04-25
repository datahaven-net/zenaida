import os
import pytest

from django.conf import settings

from automats import domains_checker

from zen import zerrors

from tests import testsupport


@pytest.mark.django_db
def test_single_domain_exist():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dc = domains_checker.DomainsChecker(
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name = 'test.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dc.event('run', [test_domain_name, ])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'INFO_ONE', 'response'),
        ('INFO_ONE', 'DONE', 'response'),
    ]
    assert len(outputs) == 4
    assert outputs[0] == [test_domain_name, ]
    assert outputs[1]['epp']['response']['result']['@code'] == '1000'
    assert outputs[2]['epp']['response']['result']['@code'] == '1000'
    assert outputs[3] == {test_domain_name: True, }


@pytest.mark.django_db
def test_single_domain_not_exist():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dc = domains_checker.DomainsChecker(
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name = 'this-domain-not-exist.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dc.event('run', [test_domain_name, ])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'DONE', 'response'),
    ]
    assert len(outputs) == 3
    assert outputs[0] == []
    assert outputs[1]['epp']['response']['result']['@code'] == '1000'
    assert outputs[2] == {test_domain_name: False, }


@pytest.mark.django_db
def test_two_domains_exist():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dc = domains_checker.DomainsChecker(
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name1 = 'test.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    test_domain_name2 = 'test-readonly.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dc.event('run', [test_domain_name1, test_domain_name2, ])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'INFO_ONE', 'response'),
        ('INFO_ONE', 'INFO_ONE', 'response'),
        ('INFO_ONE', 'DONE', 'response'),
    ]
    assert len(outputs) == 5
    assert outputs[0] == [test_domain_name1, test_domain_name2, ]
    assert outputs[1]['epp']['response']['result']['@code'] == '1000'
    assert outputs[2]['epp']['response']['result']['@code'] == '1000'
    assert outputs[3]['epp']['response']['result']['@code'] == '1000'
    assert outputs[4][test_domain_name1] is True
    assert outputs[4][test_domain_name2] is True


@pytest.mark.django_db
def test_single_domain_another_registrar():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dc = domains_checker.DomainsChecker(
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name = 'owned-by-another-registar.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dc.event('run', [test_domain_name, ])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'INFO_ONE', 'response'),
        ('INFO_ONE', 'FAILED', 'error'),
    ]
    assert len(outputs) == 3
    assert outputs[0] == [test_domain_name, ]
    assert outputs[1]['epp']['response']['result']['@code'] == '1000'
    assert isinstance(outputs[2], zerrors.EPPResponseFailed)


@pytest.mark.django_db
def test_single_domain_another_registrant():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='test-readonly.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
        add_contacts=['registrant', 'admin', ],
        epp_id_dict={
            'registrant': 'ThisIDNotExist1',
            'admin': 'ThisIDNotExist2',
        },
        nameservers=['notexist1.com', 'notexist2.com', ],
    )
    scenario = []
    dc = domains_checker.DomainsChecker(
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    dc.event('run', [tester_domain.name, ])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'INFO_ONE', 'response'),
        ('INFO_ONE', 'FAILED', 'error'),
    ]
    assert len(outputs) == 3
    assert outputs[0] == [tester_domain.name, ]
    assert outputs[1]['epp']['response']['result']['@code'] == '1000'
    assert isinstance(outputs[2], zerrors.EPPRegistrantAuthFailed)


@pytest.mark.django_db
def test_no_domains():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dc = domains_checker.DomainsChecker(
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    dc.event('run', [])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'FAILED', 'error'),
    ]
    assert len(outputs) == 1
    assert isinstance(outputs[0], zerrors.EPPCommandInvalid)


@pytest.mark.django_db
def test_skip_check():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dc = domains_checker.DomainsChecker(
        skip_check=True,
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name = 'test.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dc.event('run', [test_domain_name, ])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'INFO_ONE', 'skip-check'),
        ('INFO_ONE', 'DONE', 'response'),
    ]
    assert len(outputs) == 2
    assert outputs[0]['epp']['response']['result']['@code'] == '1000'
    assert outputs[1] == {test_domain_name: True, }


@pytest.mark.django_db
def test_skip_info():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dc = domains_checker.DomainsChecker(
        skip_info=True,
        log_events=True,
        log_transitions=True,
    )
    dc.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name = 'test.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dc.event('run', [test_domain_name, ])
    outputs = list(dc.outputs)
    del dc
    assert scenario == [
        ('AT_STARTUP', 'CHECK_MANY', 'run'),
        ('CHECK_MANY', 'INFO_ONE', 'response'),
        ('INFO_ONE', 'DONE', 'skip-info'),
    ]
    assert len(outputs) == 3
    assert outputs[0] == [test_domain_name, ]
    assert outputs[1]['epp']['response']['result']['@code'] == '1000'
    assert outputs[2] == {test_domain_name: True, }
