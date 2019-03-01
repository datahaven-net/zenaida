import os
import pytest

from django.conf import settings

from automats import domain_contacts_synchronizer

from zen import zclient

from tests import testsupport


@pytest.mark.django_db
def test_domain_update():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='test.%s' % settings.SUPPORTED_ZONES[0],
        domain_epp_id=zclient.make_epp_id(tester.email),
        tester=tester,
    )
    scenario = []
    cs = domain_contacts_synchronizer.DomainContactsSynchronizer(
        update_domain=True,
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario.append(
            (oldstate, newstate, event, )
        ),
    )
    cs.event('run', target_domain=tester_domain)
    outputs = list(cs.outputs)
    del cs
    assert scenario == [
        ('AT_STARTUP', 'SYNC_CONTACTS', 'run'),
        ('SYNC_CONTACTS', 'DOMAIN_INFO?', 'all-contacts-in-sync'),
        ('DOMAIN_INFO?', 'DOMAIN_UPDATE', 'response'),
        ('DOMAIN_UPDATE', 'DONE', 'response'),
    ]
    assert len(outputs) == 5
    assert outputs[0][0] == 'registrant'
    assert outputs[0][1]['epp']['response']['resData']['creData']['id'] == tester_domain.registrant.epp_id
    assert outputs[1][0] == 'admin'
    assert outputs[1][1]['epp']['response']['resData']['creData']['id'] == tester_domain.contact_admin.epp_id
    assert outputs[2][0] == 'billing'
    assert outputs[2][1]['epp']['response']['resData']['creData']['id'] == tester_domain.contact_billing.epp_id
    assert outputs[3][0] == 'tech'
    assert outputs[3][1]['epp']['response']['resData']['creData']['id'] == tester_domain.contact_tech.epp_id
