#!/usr/bin/env python
# domain_contacts_synchronizer.py

"""
.. module:: domain_contacts_synchronizer
.. role:: red

Zenaida domain_contacts_synchronizer() Automat

EVENTS:
    * :red:`all-contacts-in-sync`
    * :red:`error`
    * :red:`response`
    * :red:`run`
"""

#------------------------------------------------------------------------------

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat
from automats import contact_synchronizer

from zepp import zclient
from zepp import zerrors

#------------------------------------------------------------------------------

class DomainContactsSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``domain_contacts_synchronizer()`` state machine.
    """

    def __init__(self, debug_level=0, log_events=None, log_transitions=None, raise_errors=False, **kwargs):
        """
        Builds `domain_contacts_synchronizer()` state machine.
        """
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainContactsSynchronizer, self).__init__(
            name="domain_contacts_synchronizer",
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
        at creation phase of `domain_contacts_synchronizer()` machine.
        """

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_contacts_synchronizer()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_contacts_synchronizer()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'SYNC_CONTACTS'
                self.doInit(*args, **kwargs)
                self.doPrepareContacts(*args, **kwargs)
                self.doSyncContacts(*args, **kwargs)
        #---SYNC_CONTACTS---
        elif self.state == 'SYNC_CONTACTS':
            if event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'all-contacts-in-sync':
                self.state = 'DOMAIN_INFO?'
                self.doSendDomainInfo(*args, **kwargs)
        #---DOMAIN_INFO?---
        elif self.state == 'DOMAIN_INFO?':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DOMAIN_UPDATE'
                self.doPrepareDomainChange(*args, **kwargs)
                self.doSendDomainUpdate(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        #---DOMAIN_UPDATE---
        elif self.state == 'DOMAIN_UPDATE':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---DONE---
        elif self.state == 'DONE':
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
        self.target_domain = args[0]
        self.target_contacts = {}

    def doPrepareContacts(self, *args, **kwargs):
        """
        Action method.
        """
        possbile_contacts = {
            'registrant': self.target_domain.registrant,
            'admin': self.target_domain.contact_admin,
            'billing': self.target_domain.contact_billing,
            'tech': self.target_domain.contact_tech,
        }
        for role, possbile_contact in possbile_contacts.items():
            if not possbile_contact:
                continue
            self.target_contacts[role] = possbile_contact

    def doSyncContacts(self, *args, **kwargs):
        """
        Action method.
        """
        for role, contact_object in self.target_contacts.items():
            cs = contact_synchronizer.ContactSynchronizer(raise_errors=True)
            try:
                cs.event('run', contact_object)
            except Exception as exc:
                self.event('error', exc)
                break
            result = cs.outputs[0]
            if isinstance(result, Exception):
                self.event('error', result)
                break
            self.outputs.extend([
                (role, result, ),
            ])

    def doSendDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = zclient.cmd_domain_info(
                domain=self.target_domain.name,
            )
        except zerrors.EPPError as exc:
            self.log(self.debug_level, 'Exception in doSendDomainInfo: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doPrepareDomainChange(self, *args, **kwargs):
        """
        Action method.
        """
        self.add_contacts = []
        self.remove_contacts = []
        self.change_registrant = None
        current_contacts = args[0]['epp']['response']['resData']['infData']['contact']
        if not isinstance(current_contacts, list):
            current_contacts = [current_contacts, ]
        current_contacts = [{
            'type': i['@type'],
            'id': i['#text'],
        } for i in current_contacts]
        current_registrant = args[0]['epp']['response']['resData']['infData'].get('registrant', {'id': None, })
        new_contacts = []
        for role, contact_object in self.target_contacts.items():
            if role != 'registrant':
                if contact_object.epp_id:
                    new_contacts.append({'type': role, 'id': contact_object.epp_id})
        current_contacts_ids = [old_contact['id'] for old_contact in current_contacts]
        new_contacts_ids = [new_cont['id'] for new_cont in new_contacts]
        for new_cont in new_contacts:
            if new_cont['id'] not in current_contacts_ids:
                self.add_contacts.append(new_cont)
        for old_cont in current_contacts:
            if old_cont['type'] != 'registrant':
                if old_cont['id'] not in new_contacts_ids:
                    self.remove_contacts.append(old_cont)
        if 'registrant' in self.target_contacts:
            if current_registrant != self.target_contacts['registrant'].epp_id:
                self.change_registrant = self.target_contacts['registrant'].epp_id

    def doSendDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = zclient.cmd_domain_update(
                domain=self.target_domain.name,
                add_contacts_list=self.add_contacts,
                remove_contacts_list=self.remove_contacts,
                change_registrant=self.change_registrant,
            )
        except zerrors.EPPError as exc:
            self.log(self.debug_level, 'Exception in doSendDomainUpdate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

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
        else:
            self.outputs.append(Exception(
                'Unexpected response code: %s' % args[0]['epp']['response']['result']['@code']
            ))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.destroy()


