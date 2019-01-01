#!/usr/bin/env python
# domains_checker.py

"""
.. module:: domains_checker
.. role:: red

Zenaida domains_checker() Automat

EVENTS:
    * :red:`error`
    * :red:`response`
    * :red:`run`
    * :red:`skip-check`
    * :red:`skip-info`
"""

#------------------------------------------------------------------------------

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat

from back import domains

from zepp import zclient
from zepp import zerrors

#------------------------------------------------------------------------------

class DomainsChecker(automat.Automat):
    """
    This class implements all the functionality of ``domains_checker()`` state machine.
    """

    def __init__(self, verify_registrant=True, skip_check=False, skip_info=False,
                 debug_level=0, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domains_checker()` state machine.
        """
        self.skip_check = skip_check
        self.skip_info = skip_info
        self.verify_registrant = verify_registrant
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainsChecker, self).__init__(
            name="domains_checker",
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
        at creation phase of `domains_checker()` machine.
        """

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domains_checker()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domains_checker()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'CHECK_MANY'
                self.doInit(*args, **kwargs)
                self.doEppDomainCheckMany(*args, **kwargs)
        #---CHECK_MANY---
        elif self.state == 'CHECK_MANY':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isAnyExist(*args, **kwargs):
                self.state = 'DONE'
                self.doReportExisting(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'skip-check' or ( event == 'response' and self.isCode(1000, *args, **kwargs) and self.isAnyExist(*args, **kwargs) ):
                self.state = 'INFO_ONE'
                self.doReportExisting(event, *args, **kwargs)
                self.doPrepareAvailableDomains(event, *args, **kwargs)
                self.doIterateNextDomain(*args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
        #---INFO_ONE---
        elif self.state == 'INFO_ONE':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and self.isMoreAvaialble(*args, **kwargs):
                self.doReportOne(event, *args, **kwargs)
                self.doIterateNextDomain(*args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'skip-info' or ( event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isMoreAvaialble(*args, **kwargs) ):
                self.state = 'DONE'
                self.doReportOne(event, *args, **kwargs)
                self.doReportDone(event, *args, **kwargs)
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

    def isAnyExist(self, *args, **kwargs):
        """
        Condition method.
        """
        results = args[0]['epp']['response']['resData']['chkData']['cd']
        if not results:
            return False
        if not isinstance(results, list):
            results = [results, ]
        for result in results:
            if result.get('name', {}).get('@avail') == '0' and result.get('reason').lower().count('the domain exists'):
                return True
        return False

    def isMoreAvaialble(self, *args, **kwargs):
        """
        Condition method.
        """
        return len(self.available_domain_names) > 0

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_domain_names = list(args[0])
        self.current_domain_name = None

    def doPrepareAvailableDomains(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'skip-check':
            self.available_domain_names = list(self.target_domain_names)
            return
        self.available_domain_names = []
        results = args[0]['epp']['response']['resData']['chkData']['cd']
        if not results:
            return
        if not isinstance(results, list):
            results = [results, ]
        for result in results:
            name = result.get('name', {}).get('#text')
            if not name:
                self.log(self.debug_level, 'Invalid EPP response, unknown domain name: %s' % args[0])
                continue
            if result.get('name', {}).get('@avail') == '0' and result.get('reason').lower().count('the domain exists'):
                self.available_domain_names.append(name)

    def doIterateNextDomain(self, *args, **kwargs):
        """
        Action method.
        """
        self.current_domain_name = self.available_domain_names.pop()

    def doEppDomainCheckMany(self, *args, **kwargs):
        """
        Action method.
        """
        if self.skip_check:
            self.event('skip-check')
            return
        try:
            response = zclient.cmd_domain_check(
                domains=self.target_domain_names,
                raise_for_result=False,
            )
        except zerrors.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainCheckMany: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        if self.skip_info:
            self.event('skip-info')
            return
        try:
            response = zclient.cmd_domain_info(
                domain=self.current_domain_name,
            )
        except zerrors.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', exc)
        else:
            if self.verify_registrant:
                known_domain = domains.find(domain_name=self.current_domain_name)
                known_registrant_epp_id = None if not known_domain else known_domain.registrant.epp_id
                real_registrant_epp_id = response['epp']['response']['resData']['infData'].get('registrant', None)
                if real_registrant_epp_id and known_registrant_epp_id and known_registrant_epp_id != real_registrant_epp_id:
                    self.log(self.debug_level, 'Domain known to belong to another registrant: %s' % self.current_domain_name)
                    self.event('error', zerrors.EPPRegistrantAuthFailed(response=response))
                    return
            self.event('response', response)

    def doReportExisting(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'skip-check':
            return
        existing_domains = []
        results = args[0]['epp']['response']['resData']['chkData']['cd']
        if not results:
            return
        if not isinstance(results, list):
            results = [results, ]
        for result in results:
            name = result.get('name', {}).get('#text')
            if not name:
                self.log(self.debug_level, 'Invalid EPP response, unknown domain name: %s' % args[0])
                continue
            if result.get('name', {}).get('@avail') == '0' and result.get('reason').lower().count('the domain exists'):
                existing_domains.append(name)
        self.outputs.append(existing_domains)
        self.outputs.append(args[0])

    def doReportOne(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event != 'skip-info':
            self.outputs.append(args[0])

    def doReportDone(self, event, *args, **kwargs):
        """
        Action method.
        """

    def doReportFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(zerrors.EPPUnexpectedResponse(response=args[0]))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.current_domain_name = None
        self.target_domain_names = None
        self.available_domain_names = None
        self.destroy()


