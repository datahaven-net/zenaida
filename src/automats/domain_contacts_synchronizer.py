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

from epp import rpc_client
from epp import rpc_error

from zen import zdomains
from zen import zcontacts

#------------------------------------------------------------------------------

class DomainContactsSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``domain_contacts_synchronizer()`` state machine.
    """

    def __init__(self, update_domain=False,
                 skip_roles=[], skip_contact_details=False,
                 merge_duplicated_contacts=False,
                 new_registrant=None,
                 debug_level=4, log_events=None, log_transitions=None,
                 raise_errors=False,
                 **kwargs):
        """
        Builds `domain_contacts_synchronizer()` state machine.
        """
        self.target_domain = None
        self.domain_to_be_updated = update_domain
        self.skip_roles = skip_roles
        self.skip_contact_details = skip_contact_details
        self.merge_duplicated_contacts = merge_duplicated_contacts
        self.new_registrant = new_registrant
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        self.accept_code_2304 = kwargs.pop('accept_code_2304', False)
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

    @property
    def label(self):
        if not self.target_domain:
            return '%s(%s)' % (self.id, self.state)
        return '%s[%s](%s)' % (self.id, self.target_domain.name or '?', self.state)

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
        result_code = int(args[1]['epp']['response']['result']['@code'])
        if result_code == 2304 and self.accept_code_2304:
            result_code = 1000
        return args[0] == result_code

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
            'admin': self.target_domain.contact_admin,
            'billing': self.target_domain.contact_billing,
            'tech': self.target_domain.contact_tech,
            'registrant': self.target_domain.registrant,
        }
        for role, possbile_contact in possible_contacts.items():
            if role in self.skip_roles:
                continue
            if not possbile_contact:
                continue
            self.target_contacts[role] = possbile_contact
        if self.merge_duplicated_contacts:
            self.target_contacts = zcontacts.merge_contacts(self.target_contacts)
            for role in ['admin', 'billing', 'tech', ]:
                if self.target_contacts.get(role):
                    zdomains.domain_join_contact(self.target_domain, role, self.target_contacts[role])
            self.target_domain.refresh_from_db()
        if self.new_registrant:
            if self.new_registrant.epp_id != self.target_domain.registrant.epp_id:
                self.target_domain = zdomains.domain_change_registrant(self.target_domain, self.new_registrant)
                self.target_domain.refresh_from_db()

    def doSyncContacts(self, *args, **kwargs):
        """
        Action method.
        """
        for role in sorted(self.target_contacts.keys()):
            contact_object = self.target_contacts[role]
            if contact_object.epp_id and self.skip_contact_details:
                self.outputs.extend([
                    (role, None, ),
                ])
                continue
            cs = contact_synchronizer.ContactSynchronizer(raise_errors=True)
            try:
                cs.event('run', contact_object)
            except Exception as exc:
                self.log(self.debug_level, 'Exception in ContactSynchronizer: %s' % exc)
                del cs
                self.event('error', exc)
                break
            outputs = list(cs.outputs)
            del cs
            result = outputs[0]
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
            response = rpc_client.cmd_domain_info(
                domain=self.target_domain.name,
            )
        except rpc_error.EPPError as exc:
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
        self.add_contacts, self.remove_contacts, self.change_registrant = zdomains.compare_contacts(
            domain_object=self.target_domain,
            domain_info_response=args[0],
            target_contacts=list(self.target_contacts.items()),
        )

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_domain_update(
                domain=self.target_domain.name,
                add_contacts_list=self.add_contacts,
                remove_contacts_list=self.remove_contacts,
                change_registrant=self.change_registrant,
            )
        except rpc_error.EPPError as exc:
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
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.add_contacts = None
        self.remove_contacts = None
        self.change_registrant = None
        self.domain_to_be_updated = None
        self.skip_roles = None
        self.target_domain = None
        self.target_contacts = None
        self.destroy()
