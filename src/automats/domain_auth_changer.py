#!/usr/bin/env python
# domain_auth_changer.py

"""
.. module:: domain_auth_changer
.. role:: red

Zenaida domain_auth_changer() Automat

EVENTS:
    * :red:`error`
    * :red:`response`
    * :red:`run`
"""

#------------------------------------------------------------------------------

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat

from epp import rpc_client
from epp import rpc_error

from zen import zdomains

#------------------------------------------------------------------------------

class DomainAuthChanger(automat.Automat):
    """
    This class implements all the functionality of ``domain_auth_changer()`` state machine.
    """

    def __init__(self, debug_level=4, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domain_auth_changer()` state machine.
        """
        self.target_domain = None
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainAuthChanger, self).__init__(
            name="domain_auth_changer",
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

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_auth_changer()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_auth_changer()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'INFO?'
                self.doInit(*args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
        #---INFO?---
        elif self.state == 'INFO?':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'SET_AUTH!'
                self.doEppDomainUpdateAuthCode(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---SET_AUTH!---
        elif self.state == 'SET_AUTH!':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doDBUpdateDomain(*args, **kwargs)
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
        self.target_domain = kwargs['target_domain']
        self.new_auth_info = kwargs.get('new_auth_info', None)
        if not self.new_auth_info:
            self.new_auth_info = zdomains.generate_random_auth_info()

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_domain_info(
                domain=self.target_domain.name,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doEppDomainUpdateAuthCode(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_domain_update(
                domain=self.target_domain.name,
                auth_info=self.new_auth_info,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainUpdateAuthCode: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doDBUpdateDomain(self, *args, **kwargs):
        """
        Action method.
        """
        zdomains.domain_set_auth_key(self.target_domain, self.new_auth_info)

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(args[0])

    def doReportFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        elif event == 'response':
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.target_domain = None
        self.new_auth_info = None
        self.destroy()
