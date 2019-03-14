#!/usr/bin/env python
# domain_refresher.py
#


"""
.. module:: domain_refresher
.. role:: red

Zenaida domain_refresher() Automat

EVENTS:
    * :red:`error`
    * :red:`response`
    * :red:`run`
"""


from automats import automat


_DomainRefresher = None


def A(event=None, *args, **kwargs):
    """
    Access method to interact with `domain_refresher()` machine.
    """
    global _DomainRefresher
    if event is None:
        return _DomainRefresher
    if _DomainRefresher is None:
        # TODO: set automat name and starting state here
        _DomainRefresher = DomainRefresher(name='domain_refresher', state='AT_STARTUP')
    if event is not None:
        _DomainRefresher.automat(event, *args, **kwargs)
    return _DomainRefresher


def Destroy():
    """
    Destroy `domain_refresher()` automat and remove its instance from memory.
    """
    global _DomainRefresher
    if _DomainRefresher is None:
        return
    _DomainRefresher.destroy()
    del _DomainRefresher
    _DomainRefresher = None


class DomainRefresher(automat.Automat):
    """
    This class implements all the functionality of ``domain_refresher()`` state machine.
    """

    def __init__(self, debug_level=0, log_events=False, log_transitions=False, publish_events=False, **kwargs):
        """
        Builds `domain_refresher()` state machine.
        """
        super(DomainRefresher, self).__init__(
            name="domain_refresher",
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
        at creation phase of `domain_refresher()` machine.
        """

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_refresher()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_refresher()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'EXISTS?'
                self.doInit(*args, **kwargs)
                self.doEppDomainCheck(*args, **kwargs)
        #---EXISTS?---
        elif self.state == 'EXISTS?':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isDomainExist(*args, **kwargs):
                self.state = 'DONE'
                self.doReportNotExist(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and self.isDomainExist(*args, **kwargs):
                self.state = 'INFO?'
                self.doEppDomainInfo(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportCheckFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        #---DONE---
        elif self.state == 'DONE':
            pass
        #---INFO?---
        elif self.state == 'INFO?':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs):
                self.state = 'FAILED'
                self.doReportInfoFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)


    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """

    def isDomainExist(self, *args, **kwargs):
        """
        Condition method.
        """

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """

    def doReportInfoFailed(event, *args, **kwargs):
        """
        Action method.
        """

    def doReportCheckFailed(event, *args, **kwargs):
        """
        Action method.
        """

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.destroy()

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """

    def doEppDomainCheck(self, *args, **kwargs):
        """
        Action method.
        """

    def doReportNotExist(self, *args, **kwargs):
        """
        Action method.
        """

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """

