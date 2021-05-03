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

import logging

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat

from epp import rpc_client
from epp import rpc_error

from zen import zdomains
from zen import zerrors

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainsChecker(automat.Automat):
    """
    This class implements all the functionality of ``domains_checker()`` state machine.
    """

    def __init__(self, verify_registrant=True, skip_check=False, skip_info=False, stop_on_error=False,
                 debug_level=4, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domains_checker()` state machine.
        """
        self.target_domain_names = None
        self.skip_check = skip_check
        self.skip_info = skip_info
        self.verify_registrant = verify_registrant
        self.stop_on_error = stop_on_error
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

    @property
    def label(self):
        if not self.target_domain_names:
            return '%s(%s)' % (self.id, self.state)
        if len(self.target_domain_names) > 1:
            return '%s[%d](%s)' % (self.id, len(self.target_domain_names), self.state)
        return '%s[%s](%s)' % (self.id, self.target_domain_names[0], self.state)

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
                self.doReportDone(event, *args, **kwargs)
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
        self.auth_info = kwargs.get('auth_info')
        self.check_results = {dn: False for dn in self.target_domain_names}
        self.current_domain_name = None

    def doPrepareAvailableDomains(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'skip-check':
            self.existing_domains = list(self.target_domain_names)
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
                logger.error('invalid EPP response, unknown domain name: %s', args[0])
                continue
            if result.get('name', {}).get('@avail') == '0' and result.get('reason').lower().count('the domain exists'):
                self.available_domain_names.append(name)
        self.existing_domains = list(self.available_domain_names)

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
        if not self.target_domain_names:
            self.event('error', zerrors.CommandInvalid('No domains specified'))
            return
        try:
            response = rpc_client.cmd_domain_check(
                domains=self.target_domain_names,
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainCheckMany: %s' % exc)
            self.event('error', exc)
        else:
            _errors = self._do_find_errors_in_response(response)
            if _errors:
                self.event('error', _errors[0])
            else:
                self.event('response', response)

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        if self.skip_info:
            self.check_results = {dn: (dn in self.existing_domains) for dn in self.target_domain_names}
            self.event('skip-info')
            return
        try:
            response = rpc_client.cmd_domain_info(
                domain=self.current_domain_name,
                auth_info=self.auth_info or None,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', exc)
        else:
            if self.verify_registrant:
                known_domain = zdomains.domain_find(domain_name=self.current_domain_name)
                known_registrant_epp_id = None if not known_domain else known_domain.registrant.epp_id
                real_registrant_epp_id = response['epp']['response']['resData']['infData'].get('registrant', None)
                if real_registrant_epp_id and known_registrant_epp_id and known_registrant_epp_id != real_registrant_epp_id:
                    logger.warn('domain %s suppose to belong to another registrant: %r, but received another id: %r', 
                                 self.current_domain_name, known_registrant_epp_id, real_registrant_epp_id)
                    self.event('error', zerrors.RegistrantAuthFailed(response=response))
                    return
            self.check_results[self.current_domain_name] = True
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
            self.outputs.append(rpc_error.EPPResponseEmpty())
            return
        if not isinstance(results, list):
            results = [results, ]
        for result in results:
            name = result.get('name', {}).get('#text')
            if not name:
                logger.error('unexpected EPP response, unknown domain name: %s', args[0])
                continue
            if result.get('name', {}).get('@avail') == '0':
                if result.get('reason').lower().count('the domain exists'):
                    existing_domains.append(name)
                    self.check_results[name] = True
                else:
                    self.check_results[name] = rpc_error.exception_from_response(response=args[0])
            else:
                self.check_results[name] = False
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
        self.outputs.append(self.check_results)

    def doReportFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.check_results = None
        self.current_domain_name = None
        self.target_domain_names = None
        self.existing_domains = None
        self.available_domain_names = None
        self.destroy()

    def _do_find_errors_in_response(self, response):
        results = response['epp']['response']['resData']['chkData']['cd']
        if not results:
            logger.error('unexpected EPP response, no results')
            return [rpc_error.EPPResponseEmpty(), ]
        if not isinstance(results, list):
            results = [results, ]
        for result in results:
            if not result.get('name', {}).get('#text'):
                logger.error('unexpected EPP response, unknown domain name: %s', response)
                return [rpc_error.EPPResponseEmpty(), ]
            if result.get('name', {}).get('@avail') == '0':
                reason = result.get('reason').lower()
                if reason.count('non-supported zone'):
                    return [zerrors.NonSupportedZone(), ]
                if not reason.count('the domain exists'):
                    return [rpc_error.exception_from_response(response=response), ]
        return []
