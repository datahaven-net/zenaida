#!/usr/bin/env python
# contact_synchronizer.py

"""
.. module:: contact_synchronizer
.. role:: red

Zenaida contact_synchronizer() Automat

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

from zen import zcontacts

#------------------------------------------------------------------------------

class ContactSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``contact_synchronizer()`` state machine.
    """

    def __init__(self, debug_level=4, log_events=None, log_transitions=None, raise_errors=False, **kwargs):
        """
        Builds `contact_synchronizer()` state machine.
        """
        self.target_contact = None
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(ContactSynchronizer, self).__init__(
            name="contact_synchronizer",
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
        if not self.target_contact:
            return '%s(%s)' % (self.id, self.state)
        return '%s[%s](%s)' % (self.id, self.target_contact.epp_id or '?', self.state)

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
                self.doInit(*args, **kwargs)
                self.doPrepareCreate(*args, **kwargs)
                self.doEppContactCreate(*args, **kwargs)
            elif event == 'run' and self.isKnownEPPid(*args, **kwargs):
                self.state = 'CONTACT_UPDATE'
                self.doInit(*args, **kwargs)
                self.doPrepareUpdate(*args, **kwargs)
                self.doEppContactUpdate(*args, **kwargs)
        #---CONTACT_RECREATE---
        elif self.state == 'CONTACT_RECREATE':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doWriteDB(*args, **kwargs)
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---CONTACT_UPDATE---
        elif self.state == 'CONTACT_UPDATE':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) and not self.isCode(2303, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(2303, *args, **kwargs):
                self.state = 'CONTACT_RECREATE'
                self.doPrepareRetry(*args, **kwargs)
                self.doEppContactCreate(*args, **kwargs)
        #---CONTACT_CREATE---
        elif self.state == 'CONTACT_CREATE':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) and not self.isCode(2303, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(2303, *args, **kwargs):
                self.state = 'CONTACT_RECREATE'
                self.doPrepareRetry(*args, **kwargs)
                self.doEppContactCreate(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doWriteDB(*args, **kwargs)
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
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
        return bool(args[0].epp_id)

    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0] == int(args[1]['epp']['response']['result']['@code'])

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_contact = args[0]

    def doPrepareCreate(self, *args, **kwargs):
        """
        Action method.
        """
        self.contact_info = zcontacts.to_dict(self.target_contact)
        self.contact_info['id'] = rpc_client.make_epp_id(self.contact_info['email'])

    def doPrepareUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        self.contact_info = zcontacts.to_dict(self.target_contact)
        self.contact_info['id'] = self.target_contact.epp_id

    def doPrepareRetry(self, *args, **kwargs):
        """
        Action method.
        """
        # small workaround for situations when that contact already exists on the server,
        # epp_id is generated randomly so there is a chance you hit already existing object
        self.contact_info['id'] = rpc_client.make_epp_id(self.contact_info['email']) + 'a'

    def doEppContactCreate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_contact_create(
                contact_id=self.contact_info['id'],
                email=self.contact_info['email'],
                voice=self.contact_info['voice'],
                fax=self.contact_info['fax'],
                # auth_info=auth_info,
                contacts_list=self.contact_info['contacts'],
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppContactCreate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doEppContactUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_contact_update(
                contact_id=self.contact_info['id'],
                email=self.contact_info['email'],
                voice=self.contact_info['voice'],
                fax=self.contact_info['fax'],
                # auth_info=auth_info,
                contacts_list=self.contact_info['contacts'],
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppContactUpdate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doWriteDB(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_contact.epp_id = args[0]['epp']['response']['resData']['creData']['id']
        self.target_contact.save()

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """
        # TODO: log some positive history in the DB here
        self.outputs.append(args[0])

    def doReportFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        # TODO: log error in the history here
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.target_contact = None
        self.destroy(**kwargs)
