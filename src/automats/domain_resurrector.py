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

from zen import zclient
from zen import zerrors

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainResurrector(automat.Automat):
    """
    This class implements all the functionality of ``domain_resurrector()`` state machine.
    """

    def __init__(self, debug_level=0, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domain_resurrector()` state machine.
        """
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
            self.event('verify-failed', exc)
        else:
            self.outputs.extend(list(dc.outputs))
            del dc
            self.event('verify-ok')

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        pending_delete_status = None
        if self.target_domain.epp_statuses:
            pending_delete_status = self.target_domain.epp_statuses.get('pendingDelete')
        if not pending_delete_status:
            logger.error('failed to restore domain, pendingDelete status is not set')
            self.event('error', Exception('failed to restore domain, pendingDelete status is not set'))
            return

        pending_delete_date = re.search('\d\d\d\d-\d\d-\d\d \d\d:\d\d .\d\d\d\d', pending_delete_status)
        if pending_delete_date:
            t = pending_delete_date.group(0)
            pending_delete_date = (
                datetime.datetime.strptime(t[:-6], '%Y-%m-%d %H:%M') + datetime.timedelta(hours=int(t[-5:-2]))
            ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        rgp_restore_report = {}
        rgp_restore = None
        if pending_delete_date:
            rgp_restore_report={
                "pre_data": kwargs.get('pre_data', 'Pre-delete registration data not provided'),
                "post_data": kwargs.get('post_data', 'Post-restore registration data not provided'),
                "del_time": kwargs.get('del_time', pending_delete_date),
                "res_time": kwargs.get('res_time', datetime.datetime.strftime(datetime.datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ')),
                "res_reason": kwargs.get('res_reason', 'Customer %s requested to restore domain' % self.target_domain.owner.email),
                "statement1": kwargs.get('statement1', 'The information in this report is correct'),
                "statement2": kwargs.get('statement2', 'Generated by .AI site automation process'),
                "other": kwargs.get('other', 'No other information provided'),
            }
        else:
            rgp_restore = True

        try:
            response = zclient.cmd_domain_update(
                domain=self.target_domain.name,
                rgp_restore=rgp_restore,
                rgp_restore_report=rgp_restore_report,
            )
        except zerrors.EPPError as exc:
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
            self.event('refresh-failed', exc)
        else:
            self.outputs.extend(list(dr.outputs))
            del dr
            self.event('refresh-ok')

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
            self.outputs.append(zerrors.EPPUnexpectedResponse(response=args[0]))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.target_domain = None
        self.destroy()
