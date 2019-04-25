import os
import pytest

from django.conf import settings

from automats import domain_refresher

from tests import testsupport


@pytest.mark.django_db
def test_domain_not_exist():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    scenario = []
    dr = domain_refresher.DomainRefresher(
        log_events=True,
        log_transitions=True,
    )
    dr.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name = 'this-domain-not-exist.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dr.event(
        'run',
        domain_name=test_domain_name,
        change_owner_allowed=True,
        refresh_contacts=True,
    )
    outputs = list(dr.outputs)
    del dr
    assert scenario == [
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'DONE', 'response'),
    ]
    assert len(outputs) == 1
    assert outputs[0] is None


@pytest.mark.django_db
def test_domain_refreshed():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    testsupport.prepare_tester_registrant(epp_id='tester480126cf6j', create_new=True)
    scenario = []
    dr = domain_refresher.DomainRefresher(
        log_events=True,
        log_transitions=True,
    )
    dr.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    test_domain_name = 'test.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0]
    dr.event(
        'run',
        domain_name=test_domain_name,
        change_owner_allowed=True,
        refresh_contacts=True,
    )
    outputs = list(dr.outputs)
    del dr
    assert scenario == [
        ('AT_STARTUP', 'EXISTS?', 'run'),
        ('EXISTS?', 'INFO?', 'response'),
        ('INFO?', 'CONTACTS?', 'response'),
        ('CONTACTS?', 'DONE', 'all-contacts-received'),
    ]
    assert len(outputs) == 5
    assert outputs[0]['epp']['response']['result']['@code'] == '1000'
    assert outputs[1]['epp']['response']['result']['@code'] == '1000'
    assert outputs[2]['epp']['response']['result']['@code'] == '1000'
    assert outputs[3]['epp']['response']['result']['@code'] == '1000'
    assert outputs[4]['epp']['response']['result']['@code'] == '1000'
