#!/usr/bin/env python
# domain_resurrector.py

"""
.. module:: domain_resurrector
.. role:: red

Zenaida domain_resurrector() Automat

EVENTS:
    * :red:`error`
    * :red:`refresh-failed`
    * :red:`refresh-ok`
    * :red:`renew-failed`
    * :red:`renew-ok`
    * :red:`response`
    * :red:`run`
    * :red:`verify-failed`
    * :red:`verify-ok`
"""

#------------------------------------------------------------------------------

import logging
import datetime
import re

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat
from automats import domains_checker
from automats import domain_refresher
from automats import domain_synchronizer

from epp import rpc_client
from epp import rpc_error

from zen import zdomains

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainResurrector(automat.Automat):
    """
    This class implements all the functionality of ``domain_resurrector()`` state machine.
    """

    def __init__(self, debug_level=4, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domain_resurrector()` state machine.
        """
        self.target_domain = None
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainResurrector, self).__init__(
            name="domain_resurrector",
            state="AT_STARTUP",
            outputs=[],
            debug_level=debug_level,
            log_events=log_events,
            log_transitions=log_transitions,
            raise_errors=raise_errors,
            **kwargs
        )

    @property
    def label(self):
        if not self.target_domain:
            return '%s(%s)' % (self.id, self.state)
        return '%s[%s](%s)' % (self.id, self.target_domain.name or '?', self.state)

    def init(self):
        """
        Method to initialize additional variables and flags
        at creation phase of `domain_resurrector()` machine.
        """

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_resurrector()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_resurrector()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'VERIFY?'
                self.doInit(*args, **kwargs)
                self.doRunDomainsChecker(*args, **kwargs)
        #---RESTORE!---
        elif self.state == 'RESTORE!':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'REFRESH'
                self.doRunDomainRefresher(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---VERIFY?---
        elif self.state == 'VERIFY?':
            if event == 'verify-failed':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'verify-ok':
                self.state = 'RESTORE!'
                self.doEppDomainUpdate(*args, **kwargs)
        #---REFRESH---
        elif self.state == 'REFRESH':
            if event == 'refresh-failed':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'refresh-ok':
                self.state = 'RENEW'
                self.doRunDomainSynchronizer(*args, **kwargs)
        #---RENEW---
        elif self.state == 'RENEW':
            if event == 'renew-failed':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'renew-ok':
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---DONE---
        elif self.state == 'DONE':
            pass
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        return None

    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0] == int(args[1]['epp']['response']['result']['@code'])

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_domain = kwargs['domain_object']

    def doRunDomainsChecker(self, *args, **kwargs):
        """
        Action method.
        """
        dc = domains_checker.DomainsChecker(
            skip_info=False,
            verify_registrant=False,
            stop_on_error=True,
            log_events=self.log_events,
            log_transitions=self.log_transitions,
            raise_errors=self.raise_errors,
        )
        try:
            dc.event('run', [self.target_domain.name, ])
        except Exception as exc:
            self.log(self.debug_level, 'Exception in DomainsChecker: %s' % exc)
            del dc
            self.event('verify-failed', exc)
            return
        self.outputs.extend(list(dc.outputs))
        del dc
        domain_check_result = self.outputs[-1].get(self.target_domain.name)
        if isinstance(domain_check_result, Exception):
            self.event('verify-failed', domain_check_result)
            return
        if not domain_check_result:
            self.event('verify-failed', Exception('domain %r not exist' % self.target_domain.name))
            return
        if self.target_domain:
            zdomains.domain_update_statuses(
                domain_object=self.target_domain,
                domain_info_response=self.outputs[-2],
            )
        self.event('verify-ok')

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        pending_delete_status = None
        if self.target_domain.epp_statuses:
            pending_delete_status = 'pendingDelete' in self.target_domain.epp_statuses
        if not pending_delete_status:
            logger.error('failed to restore domain, pendingDelete status is not set')
            self.event('error', Exception('failed to restore domain, pendingDelete status is not set'))
            return
        pending_delete_status_info = self.target_domain.epp_statuses.get('pendingDelete')
        pending_delete_date = None
        try:
            if pending_delete_status_info:
                pending_delete_date = re.search('\d\d\d\d-\d\d-\d\d \d\d:\d\d .\d\d\d\d', pending_delete_status)
            if pending_delete_date:
                t = pending_delete_date.group(0)
                pending_delete_date = (
                    datetime.datetime.strptime(t[:-6], '%Y-%m-%d %H:%M') + datetime.timedelta(hours=int(t[-5:-2]))
                ).strftime('%Y-%m-%dT%H:%M:%SZ')
        except Exception as exc:
            logger.warn('not able to recognize pendingDelete date from the pendingDelete status info, populate from expiry date')
        if not pending_delete_date:
            pending_delete_date = self.target_domain.expiry_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        rgp_restore_report={
            "pre_data": kwargs.get('pre_data', 'Pre-delete registration data not provided'),
            "post_data": kwargs.get('post_data', 'Post-restore registration data not provided'),
            "res_time": kwargs.get('res_time', datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ')),
            "del_time": kwargs.get('del_time', pending_delete_date),
            "res_reason": kwargs.get('res_reason', 'Customer %s requested to restore domain' % self.target_domain.owner.email),
            "statement1": kwargs.get('statement1', 'The information in this report is correct'),
            "statement2": kwargs.get('statement2', 'Generated by .AI site automation process'),
            "other": kwargs.get('other', 'No other information provided'),
        }
        try:
            response_restore_request = rpc_client.cmd_domain_update(
                domain=self.target_domain.name,
                rgp_restore=True,
                rgp_restore_report={},
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainUpdate after restore request: %s' % exc)
            self.event('error', exc)
            return
        try:
            response = rpc_client.cmd_domain_update(
                domain=self.target_domain.name,
                rgp_restore=None,
                rgp_restore_report=rgp_restore_report,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainUpdate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doRunDomainRefresher(self, *args, **kwargs):
        """
        Action method.
        """
        dr = domain_refresher.DomainRefresher(
            log_events=self.log_events,
            log_transitions=self.log_transitions,
            raise_errors=self.raise_errors,
        )
        try:
            dr.event('run',
                domain_name=self.target_domain.name,
                change_owner_allowed=False,
                refresh_contacts=False,
            )
        except Exception as exc:
            self.log(self.debug_level, 'Exception in DomainRefresher: %s' % exc)
            del dr
            self.event('refresh-failed', exc)
        else:
            self.outputs.extend(list(dr.outputs))
            del dr
            self.event('refresh-ok')

    def doRunDomainSynchronizer(self, *args, **kwargs):
        """
        Action method.
        """
        ds = domain_synchronizer.DomainSynchronizer(
            log_events=self.log_events,
            log_transitions=self.log_transitions,
            raise_errors=self.raise_errors,
            accept_code_2304=True,
        )
        try:
            ds.event('run', self.target_domain,
                sync_contacts=False,
                sync_nameservers=False,
                # renew_years=settings.ZENAIDA_DOMAIN_RENEW_YEARS,
                save_to_db=True,
            )
        except Exception as exc:
            self.log(self.debug_level, 'Exception in DomainRefresher: %s' % exc)
            del ds
            self.event('refresh-failed', exc)
        else:
            self.outputs.extend(list(ds.outputs))
            del ds
            self.event('renew-ok')

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """
        if args and args[0]:
            self.outputs.append(args[0])

    def doReportFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event in ['error', 'verify-failed', ]:
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.target_domain = None
        self.destroy()
