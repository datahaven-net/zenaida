#!/usr/bin/env python
# contact_synchronizer.py

"""
.. module:: contact_synchronizer
.. role:: red

Zenaida contact_synchronizer() Automat

EVENTS:
    * :red:`response`
    * :red:`run`
"""

#------------------------------------------------------------------------------

from automats import automat

from back import contacts

from zepp import client

#------------------------------------------------------------------------------

class ContactSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``contact_synchronizer()`` state machine.
    """

    def __init__(self, debug_level=0, log_events=False, log_transitions=False, **kwargs):
        """
        Builds `contact_synchronizer()` state machine.
        """
        super(ContactSynchronizer, self).__init__(
            name="contact_synchronizer",
            state="AT_STARTUP",
            debug_level=debug_level,
            log_events=log_events,
            log_transitions=log_transitions,
            **kwargs
        )

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `contact_synchronizer()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `contact_synchronizer()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run' and not self.isKnownEPPid(*args, **kwargs):
                self.state = 'CONTACT_CREATE'
                self.doPrepareCreate(*args, **kwargs)
                self.doSendContactCreate(*args, **kwargs)
            elif event == 'run' and self.isKnownEPPid(*args, **kwargs):
                self.state = 'CONTACT_UPDATE'
                self.doPrepareUpdate(*args, **kwargs)
                self.doSendContactUpdate(*args, **kwargs)
        #---CONTACT_RECREATE---
        elif self.state == 'CONTACT_RECREATE':
            if event == 'response' and not self.isCode(1000):
                self.state = 'FAILED'
                self.doReportFailed(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---CONTACT_UPDATE---
        elif self.state == 'CONTACT_UPDATE':
            if event == 'response' and not self.isCode(1000):
                self.state = 'FAILED'
                self.doReportFailed(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---CONTACT_CREATE---
        elif self.state == 'CONTACT_CREATE':
            if event == 'response' and self.isCode(2303):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and not self.isCode(1000) and not self.isCode(2303):
                self.state = 'FAILED'
                self.doReportFailed(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(2303):
                self.state = 'CONTACT_RECREATE'
                self.doPrepareRetry(*args, **kwargs)
                self.doSendContactCreate(*args, **kwargs)
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        #---DONE---
        elif self.state == 'DONE':
            pass
        return None

    def isKnownEPPid(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0].epp_id != ''

    def doPrepareCreate(self, *args, **kwargs):
        """
        Action method.
        """
        self.contact_info = contacts.to_dict(args[0])
        self.contact_info['id'] = client.make_epp_id(self.contact_info['email'])

    def doPrepareUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        self.contact_info = contacts.to_dict(args[0])
        self.contact_info['id'] = args[0].epp_id

    def doPrepareRetry(self, *args, **kwargs):
        """
        Action method.
        """
        # small workaround for situations when that contact already exists on the server,
        # epp_id is generated randomly so there is a chance you hit already existing object
        self.contact_info['id'] = client.make_epp_id('a' + self.contact_info['email'])

    def doSendContactCreate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = client.cmd_contact_create(
                contact_id=self.contact_info['id'],
                email=self.contact_info['email'],
                voice=self.contact_info['voice'],
                fax=self.contact_info['fax'],
                # auth_info=auth_info,
                contacts_list=self.contact_info['contacts'],
            )
        except client.EPPResponseFailed as exc:
            self.log(self.debug_level, 'Exception in doSendContactCreate: %r' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)
#             if ret['epp']['response']['result']['@code'] != '1000':
#                 if ret['epp']['response']['result']['@code'] != '2302':
#                     raise epp_client.EPPCommandFailed(message='EPP contact_create failed with error code: %s' % (
#                         ret['epp']['response']['result']['@code'], ))

    def doSendContactUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = client.cmd_contact_update(
                contact_id=self.contact_info['id'],
                email=self.contact_info['email'],
                voice=self.contact_info['voice'],
                fax=self.contact_info['fax'],
                # auth_info=auth_info,
                contacts_list=self.contact_info['contacts'],
            )
        except client.EPPResponseFailed as exc:
            self.log(self.debug_level, 'Exception in doSendContactCreate: %r' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doReportDone(self, *args, **kwargs):
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
        self.destroy(**kwargs)
