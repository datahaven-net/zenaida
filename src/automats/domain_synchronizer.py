#!/usr/bin/env python
# domain_synchronizer.py
#


"""
.. module:: domain_synchronizer
.. role:: red

Zenaida domain_synchronizer() Automat

EVENTS:
    * :red:`contacts-ok`
    * :red:`error`
    * :red:`nameservers-ok`
    * :red:`response`
    * :red:`run`
"""

#------------------------------------------------------------------------------

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat

#------------------------------------------------------------------------------

class DomainSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``domain_synchronizer()`` state machine.
    """

    def __init__(self, debug_level=0, log_events=None, log_transitions=None, raise_errors=False, **kwargs):
        """
        Builds `domain_synchronizer()` state machine.
        """
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainSynchronizer, self).__init__(
            name="domain_synchronizer",
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
        at creation phase of `domain_synchronizer()` machine.
        """

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_synchronizer()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_synchronizer()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---EXISTS?---
        if self.state == 'EXISTS?':
            if event == 'response' and not self.isDomainExist(*args, **kwargs):
                self.state = 'CONTACTS'
                self.doRunDomainContactsSync(*args, **kwargs)
            elif event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isDomainExist(*args, **kwargs):
                self.state = 'OWNER?'
                self.doEppDomainInfo(*args, **kwargs)
        #---OWNER?---
        elif self.state == 'OWNER?':
            if event == 'response' and not self.isSameRegistrant(*args, **kwargs):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isSameRegistrant(*args, **kwargs):
                self.state = 'CONTACTS'
                self.doRunDomainContactsSync(*args, **kwargs)
        #---AT_STARTUP---
        elif self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'EXISTS?'
                self.doInit(*args, **kwargs)
                self.doEppDomainCheck(*args, **kwargs)
        #---CONTACTS---
        elif self.state == 'CONTACTS':
            if event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'contacts-ok':
                self.state = 'NAMESERVERS'
                self.doRunDomainNameserversSync(*args, **kwargs)
        #---NAMESERVERS---
        elif self.state == 'NAMESERVERS':
            if event == 'nameservers-ok' and not self.isDomainToBeCreated(*args, **kwargs):
                self.state = 'READ'
                self.doEppDomainInfo(*args, **kwargs)
            elif event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'nameservers-ok' and self.isDomainToBeCreated(*args, **kwargs):
                self.state = 'CREATE!'
                self.doEppDomainCreate(*args, **kwargs)
        #---CREATE!---
        elif self.state == 'CREATE!':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'READ'
                self.doDBWriteDomain(*args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
        #---READ---
        elif self.state == 'READ':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'UPDATE!'
                self.doEppDomainUpdate(*args, **kwargs)
        #---UPDATE!---
        elif self.state == 'UPDATE!':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isDomainToBeRenew(*args, **kwargs):
                self.state = 'DONE'
                self.doReportSuccess(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and self.isDomainToBeRenew(*args, **kwargs):
                self.state = 'RENEW'
                self.doEppDomainRenew(*args, **kwargs)
        #---RENEW---
        elif self.state == 'RENEW':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doDBWriteDomain(*args, **kwargs)
                self.doReportSuccess(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---DONE---
        elif self.state == 'DONE':
            pass
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        return None

    def isDomainToBeCreated(self, *args, **kwargs):
        """
        Condition method.
        """

    def isDomainExist(self, *args, **kwargs):
        """
        Condition method.
        """

    def isDomainToBeRenew(self, *args, **kwargs):
        """
        Condition method.
        """

    def isSameRegistrant(self, *args, **kwargs):
        """
        Condition method.
        """

    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0] == int(args[1]['epp']['response']['result']['@code'])

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppDomainRenew(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppDomainCheck(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppDomainCreate(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """

    def doRunDomainNameserversSync(self, *args, **kwargs):
        """
        Action method.
        """

    def doRunDomainContactsSync(self, *args, **kwargs):
        """
        Action method.
        """

    def doDBWriteDomain(self, *args, **kwargs):
        """
        Action method.
        """

    def doReportSuccess(self, *args, **kwargs):
        """
        Action method.
        """

    def doReportFailed(self, *args, **kwargs):
        """
        Action method.
        """

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.destroy()


