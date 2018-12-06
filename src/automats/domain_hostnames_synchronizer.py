#!/usr/bin/env python
# domain_hostnames_synchronizer.py
#


"""
.. module:: domain_hostnames_synchronizer
.. role:: red

Zenaida domain_hostnames_synchronizer() Automat

EVENTS:
    * :red:`all-hosts-created`
    * :red:`error`
    * :red:`response`
    * :red:`run`
"""


from automats import automat


_DomainHostnamesSynchronizer = None


def A(event=None, *args, **kwargs):
    """
    Access method to interact with `domain_hostnames_synchronizer()` machine.
    """
    global _DomainHostnamesSynchronizer
    if event is None:
        return _DomainHostnamesSynchronizer
    if _DomainHostnamesSynchronizer is None:
        # TODO: set automat name and starting state here
        _DomainHostnamesSynchronizer = DomainHostnamesSynchronizer(name='domain_hostnames_synchronizer', state='AT_STARTUP')
    if event is not None:
        _DomainHostnamesSynchronizer.automat(event, *args, **kwargs)
    return _DomainHostnamesSynchronizer


def Destroy():
    """
    Destroy `domain_hostnames_synchronizer()` automat and remove its instance from memory.
    """
    global _DomainHostnamesSynchronizer
    if _DomainHostnamesSynchronizer is None:
        return
    _DomainHostnamesSynchronizer.destroy()
    del _DomainHostnamesSynchronizer
    _DomainHostnamesSynchronizer = None


class DomainHostnamesSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``domain_hostnames_synchronizer()`` state machine.
    """

    def __init__(self, debug_level=0, log_events=False, log_transitions=False, publish_events=False, **kwargs):
        """
        Builds `domain_hostnames_synchronizer()` state machine.
        """
        super(DomainHostnamesSynchronizer, self).__init__(
            name="domain_hostnames_synchronizer",
            state="AT_STARTUP",
            debug_level=debug_level,
            log_events=log_events,
            log_transitions=log_transitions,
            publish_events=publish_events,
            **kwargs
        )

    def init(self):
        """
        Method to initialize additional variables and flags
        at creation phase of `domain_hostnames_synchronizer()` machine.
        """

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_hostnames_synchronizer()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_hostnames_synchronizer()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---DOMAIN_INFO?---
        if self.state == 'DOMAIN_INFO?':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and self.isUpdateRequired(*args, **kwargs):
                self.state = 'HOSTS_CREATE'
                self.doEppHostCreateMany(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isUpdateRequired(*args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---AT_STARTUP---
        elif self.state == 'AT_STARTUP':
            if event == 'run' and self.isDomainInfoKnown(*args, **kwargs) and not self.isUpdateRequired(*args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'run' and not self.isDomainInfoKnown(*args, **kwargs):
                self.state = 'DOMAIN_INFO?'
                self.doEppDomainInfo(*args, **kwargs)
        #---DONE---
        elif self.state == 'DONE':
            pass
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        #---DOMAIN_UPDATE!---
        elif self.state == 'DOMAIN_UPDATE!':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---HOSTS_CREATE---
        elif self.state == 'HOSTS_CREATE':
            if event == 'all-hosts-created':
                self.state = 'DOMAIN_UPDATE!'
                self.doEppDomainUpdate(*args, **kwargs)
            elif event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)

    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """

    def isUpdateRequired(self, *args, **kwargs):
        """
        Condition method.
        """

    def isDomainInfoKnown(self, *args, **kwargs):
        """
        Condition method.
        """

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppHostCreateMany(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """

    def doReportFailed(self, event, *args, **kwargs):
        """
        Action method.
        """

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.destroy()


