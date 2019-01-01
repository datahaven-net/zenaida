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

from back import domains

from zepp import zclient
from zepp import zerrors

#------------------------------------------------------------------------------

class DomainContactsSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``domain_contacts_synchronizer()`` state machine.
    """

    def __init__(self, update_domain=False, skip_roles=[],
                 debug_level=0, log_events=None, log_transitions=None,
                 raise_errors=False,
                 **kwargs):
        """
        Builds `domain_contacts_synchronizer()` state machine.
        """
        self.domain_to_be_updated = update_domain
        self.skip_roles = skip_roles
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
            elif event == 'all-contacts-in-sync' and self.isDomainToBeUpdated(*args, **kwargs):
                self.state = 'DOMAIN_INFO?'
                self.doEppDomainInfo(*args, **kwargs)
            elif event == 'all-contacts-in-sync' and not self.isDomainToBeUpdated(*args, **kwargs):
                self.state = 'DONE'
                self.doReportContactsUpdated(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---DOMAIN_INFO?---
        elif self.state == 'DOMAIN_INFO?':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DOMAIN_UPDATE'
                self.doPrepareDomainChange(*args, **kwargs)
                self.doEppDomainUpdate(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---DOMAIN_UPDATE---
        elif self.state == 'DOMAIN_UPDATE':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'DONE'
                self.doReportDomainUpdated(*args, **kwargs)
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

    def isDomainToBeUpdated(self, *args, **kwargs):
        """
        Condition method.
        """
        return self.domain_to_be_updated

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_domain = kwargs['target_domain']

    def doPrepareContacts(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_contacts = {}
        possible_contacts = {
            'registrant': self.target_domain.registrant,
            'admin': self.target_domain.contact_admin,
            'billing': self.target_domain.contact_billing,
            'tech': self.target_domain.contact_tech,
        }
        for role, possbile_contact in possible_contacts.items():
            if role in self.skip_roles:
                continue
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
                self.log(self.debug_level, 'Exception in ContactSynchronizer: %s' % exc)
                self.event('error', exc)
                break
            result = cs.outputs[0]
            if isinstance(result, Exception):
                self.log(self.debug_level, 'Found exception in DomainContactsSynchronizer outputs: %s' % result)
                self.event('error', result)
                break
            self.outputs.extend([
                (role, result, ),
            ])
        self.event('all-contacts-in-sync')

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = zclient.cmd_domain_info(
                domain=self.target_domain.name,
            )
        except zerrors.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
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
        self.add_contacts, self.remove_contacts, self.change_registrant = domains.compare_contacts(
            domain_object=self.target_domain,
            domain_info_response=args[0],
            target_contacts=list(self.target_contacts.items()),
        )

    def doEppDomainUpdate(self, *args, **kwargs):
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
            self.log(self.debug_level, 'Exception in doEppDomainUpdate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doReportDomainUpdated(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(args[0])

    def doReportContactsUpdated(self, *args, **kwargs):
        """
        Action method.
        """
        # TODO: write positive history in DB

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
        self.add_contacts = None
        self.remove_contacts = None
        self.change_registrant = None
        self.domain_to_be_updated = None
        self.skip_roles = None
        self.destroy()


