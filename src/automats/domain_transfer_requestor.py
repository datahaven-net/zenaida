#!/usr/bin/env python
# domain_transfer_requestor.py

"""
.. module:: domain_transfer_requestor
.. role:: red

Zenaida domain_transfer_requestor() Automat

EVENTS:
    * :red:`error`
    * :red:`response`
    * :red:`run`
    * :red:`skip-info`
"""

#------------------------------------------------------------------------------

import logging

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat

from epp import rpc_client
from epp import rpc_error

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainTransferRequestor(automat.Automat):
    """
    This class implements all the functionality of ``domain_transfer_requestor()`` state machine.
    """

    def __init__(self, skip_info=False, auth_info_verify=True, debug_level=4, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domain_transfer_requestor()` state machine.
        """
        self.target_domain_name = None
        self.skip_info = skip_info
        self.auth_info_verify = auth_info_verify
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainTransferRequestor, self).__init__(
            name="domain_transfer_requestor",
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
        if not self.target_domain_name:
            return '%s(%s)' % (self.id, self.state)
        return '%s[%s](%s)' % (self.id, self.target_domain_name, self.state)

    def init(self):
        """
        Method to initialize additional variables and flags
        at creation phase of `domain_transfer_requestor()` machine.
        """
        self.latest_domain_info = None

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_transfer_requestor()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_transfer_requestor()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'DOMAIN_INFO'
                self.doInit(*args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
        #---DOMAIN_INFO---
        elif self.state == 'DOMAIN_INFO':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isTransferPossible(*args, **kwargs):
                self.state = 'FAIL'
                self.doReportTransferNotPossible(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAIL'
                self.doReportInfoFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif ( event == 'response' and self.isCode(1000, *args, **kwargs) and self.isTransferPossible(*args, **kwargs) ) or event == 'skip-info':
                self.state = 'REQUEST'
                self.doEppDomainTransfer(*args, **kwargs)
        #---REQUEST---
        elif self.state == 'REQUEST':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'SUCCESS'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAIL'
                self.doReportTransferFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---SUCCESS---
        elif self.state == 'SUCCESS':
            pass
        #---FAIL---
        elif self.state == 'FAIL':
            pass
        return None

    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0] == int(args[1]['epp']['response']['result']['@code'])

    def isTransferPossible(self, *args, **kwargs):
        """
        Condition method.
        """
        # TODO: Update state machine, this step is not needed anymore.
        # current_registrar = args[0]['epp']['response']['resData']['infData']['clID']
        # domain must not belong to the given registrar
        return True
        # return current_registrar != settings.ZENAIDA_REGISTRAR_ID

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_domain_name = kwargs['target_domain_name']
        self.auth_info = kwargs['auth_info']

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        if self.skip_info:
            self.event('skip-info')
            return
        try:
            response = rpc_client.cmd_domain_info(
                domain=self.target_domain_name,
                auth_info=self.auth_info or None,
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', exc)
        else:
            self.latest_domain_info = response
            self.event('response', response)

    def doEppDomainTransfer(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_domain_transfer(
                domain=self.target_domain_name,
                op='request',
                auth_info=self.auth_info,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainTransfer: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doReportInfoFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportTransferFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportTransferNotPossible(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(rpc_error.EPPRegistrarAuthFailed(message='Domain already belong to the registrar'))

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(True)

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.target_domain_name = None
        self.auth_info = None
        self.latest_domain_info = None
        self.destroy()


