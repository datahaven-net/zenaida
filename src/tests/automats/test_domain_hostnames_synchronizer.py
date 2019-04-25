import os
import pytest

from django.conf import settings

from automats import domain_hostnames_synchronizer

from zen import zclient

from tests import testsupport


@pytest.mark.django_db
def test_update_hostnames():
    if os.environ.get('E2E', '0') != '1':
        return pytest.skip('skip E2E')  # @UndefinedVariable
    tester = testsupport.prepare_tester_account()
    tester_domain = testsupport.prepare_tester_domain(
        domain_name='test.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
        tester=tester,
        domain_epp_id=zclient.make_epp_id(tester.email),
        add_contacts=['registrant', 'admin', ],
        nameservers=['ns1.google.com', 'ns2.google.com', 'ns3.google.com', ]
    )
    scenario1 = []
    cs1 = domain_hostnames_synchronizer.DomainHostnamesSynchronizer(
        update_domain=True,
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs1.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario1.append(
            (oldstate, newstate, event, )
        ),
    )
    cs1.event('run', target_domain=tester_domain, known_domain_info=zclient.cmd_domain_info(domain=tester_domain.name), )
    outputs1 = list(cs1.outputs)
    del cs1
    
    tester_domain.nameserver4 = 'ns4.google.com'
    tester_domain.save()
    scenario2 = []
    cs2 = domain_hostnames_synchronizer.DomainHostnamesSynchronizer(
        update_domain=True,
        log_events=True,
        log_transitions=True,
        raise_errors=True,
    )
    cs2.add_state_changed_callback(
        cb=lambda oldstate, newstate, event, *args, **kwargs: scenario2.append(
            (oldstate, newstate, event, )
        ),
    )
    cs2.event('run', target_domain=tester_domain, known_domain_info=zclient.cmd_domain_info(domain=tester_domain.name), )
    outputs2 = list(cs2.outputs)
    del cs2
    
    # one nameserver should be removed
    assert scenario1 == [
        ('AT_STARTUP', 'DOMAIN_INFO?', 'run'),
        ('DOMAIN_INFO?', 'HOSTS_CHECK', 'response'),
        ('HOSTS_CHECK', 'DOMAIN_UPDATE!', 'no-hosts-to-be-added'),
        ('DOMAIN_UPDATE!', 'DONE', 'response'),
    ]
    assert len(outputs1) == 1
    assert outputs1[0]['epp']['response']['result']['@code'] == '1000'
    # one nameserver should be added back
    assert scenario2 == [
        ('AT_STARTUP', 'DOMAIN_INFO?', 'run'),
        ('DOMAIN_INFO?', 'HOSTS_CHECK', 'response'),
        ('HOSTS_CHECK', 'HOSTS_CREATE', 'response'),
        ('HOSTS_CREATE', 'DOMAIN_UPDATE!', 'all-hosts-created'),
        ('DOMAIN_UPDATE!', 'DONE', 'response'),
    ]
    assert len(outputs2) == 1
    assert outputs2[0]['epp']['response']['result']['@code'] == '1000'
