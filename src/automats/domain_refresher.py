#!/usr/bin/env python
# domain_refresher.py

"""
.. module:: domain_refresher
.. role:: red

Zenaida domain_refresher() Automat

EVENTS:
    * :red:`all-contacts-received`
    * :red:`contacts-replaced`
    * :red:`contacts-rewrite-error`
    * :red:`domain-transferred-away`
    * :red:`error`
    * :red:`registrant-unknown`
    * :red:`response`
    * :red:`rewrite-contacts`
    * :red:`run`
"""

#------------------------------------------------------------------------------ 

import logging
import datetime

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat
from automats import domain_contacts_synchronizer

from epp import rpc_client
from epp import rpc_error

from zen import zdomains
from zen import zusers
from zen import zcontacts
from zen import zerrors

from billing import orders

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainRefresher(automat.Automat):
    """
    This class implements all the functionality of ``domain_refresher()`` state machine.
    """

    def __init__(self, debug_level=4, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domain_refresher()` state machine.
        """
        self.domain_name = None
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainRefresher, self).__init__(
            name="domain_refresher",
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
        if not self.domain_name:
            return '%s(%s)' % (self.id, self.state)
        return '%s[%s](%s)' % (self.id, self.domain_name, self.state)

    def init(self):
        """
        Method to initialize additional variables and flags
        at creation phase of `domain_refresher()` machine.
        """
        self.contacts_changed = False
        self.refresh_contacts = False  # when True, Zenaida will read contacts from back-end and update local DB
        self.rewrite_contacts = False  # when True, Zenaida will write DB contacts to the back-end
        self.domain_info_response = None
        self.received_registrant_epp_id = None
        self.received_contacts = []
        self.new_domain_contacts = {}
        self.received_nameservers = []
        self.known_registrant = None
        self.new_registrant_epp_id = None
        self.current_registrant_info = None
        self.latest_registrant_response = None
        self.current_registrant_address_info = None
        self.contacts_to_add = None
        self.contacts_to_remove = None

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
                self.doDBDeleteDomain(*args, **kwargs)
                self.doReportNotExist(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and self.isDomainExist(*args, **kwargs):
                self.state = 'INFO?'
                self.doEppDomainInfo(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportCheckFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---INFO?---
        elif self.state == 'INFO?':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and self.isContactsNeeded(*args, **kwargs):
                self.state = 'CONTACTS?'
                self.doReportDomainInfo(*args, **kwargs)
                self.doEppContactsInfoMany(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isContactsNeeded(*args, **kwargs):
                self.state = 'DONE'
                self.doDBCheckCreateDomain(*args, **kwargs)
                self.doDBCheckUpdateNameservers(*args, **kwargs)
                self.doDBCheckUpdateDomainInfo(*args, **kwargs)
                self.doCheckProcessPendingOrder(*args, **kwargs)
                self.doReportDomainInfo(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) and not self.isCode(2201, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportInfoFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'registrant-unknown':
                self.state = 'CUR_REG?'
                self.doReportDomainInfo(*args, **kwargs)
                self.doEppCurrentRegistrantInfo(*args, **kwargs)
            elif event == 'domain-transferred-away' or ( event == 'response' and self.isCode(2201, *args, **kwargs) ):
                self.state = 'DONE'
                self.doDBDeleteDomain(*args, **kwargs)
                self.doReportAnotherRegistrar(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'rewrite-contacts':
                self.state = 'UPDATE_REG'
                self.doUseExistingContacts(*args, **kwargs)
                self.doEppDomainUpdate(*args, **kwargs)
        #---CONTACTS?---
        elif self.state == 'CONTACTS?':
            if event == 'all-contacts-received':
                self.state = 'DONE'
                self.doDBCheckCreateUpdateContacts(*args, **kwargs)
                self.doDBCheckCreateDomain(*args, **kwargs)
                self.doDBCheckChangeOwner(*args, **kwargs)
                self.doDBCheckChangeContacts(*args, **kwargs)
                self.doDBCheckUpdateNameservers(*args, **kwargs)
                self.doDBCheckUpdateDomainInfo(*args, **kwargs)
                self.doCheckProcessPendingOrder(*args, **kwargs)
                self.doReportContactsInfo(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error':
                self.state = 'FAILED'
                self.doReportContactsFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---CUR_REG?---
        elif self.state == 'CUR_REG?':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportCurRegistrantFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and self.isUserAccountExists(*args, **kwargs):
                self.state = 'UPDATE_REG'
                self.doUseExistingRegistrant(*args, **kwargs)
                self.doEppDomainUpdate(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isUserAccountExists(*args, **kwargs):
                self.state = 'REWRITE_CONT'
                self.doUseReceivedRegistrantInfo(*args, **kwargs)
                self.doDBCheckCreateUserAccount(*args, **kwargs)
                self.doDBSetDomainContacts(*args, **kwargs)
                self.doRewriteDomainContacts(*args, **kwargs)
        #---UPDATE_REG---
        elif self.state == 'UPDATE_REG':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'CONTACTS?'
                self.doDBCheckCreateUserAccount(*args, **kwargs)
                self.doEppContactsInfoMany(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportDomainUpdateFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---REWRITE_CONT---
        elif self.state == 'REWRITE_CONT':
            if event == 'contacts-replaced':
                self.state = 'UPDATE_REG'
                self.doUseExistingRegistrant(*args, **kwargs)
                self.doEppDomainUpdate(*args, **kwargs)
            elif event == 'contacts-rewrite-error':
                self.state = 'FAILED'
                self.doReportContactsFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        #---DONE---
        elif self.state == 'DONE':
            pass
        return None

    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0] == int(args[1]['epp']['response']['result']['@code'])

    def isDomainExist(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0]['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '0'

    def isContactsNeeded(self, *args, **kwargs):
        """
        Condition method.
        """
        return self.refresh_contacts or self.contacts_changed

    def isUserAccountExists(self, *args, **kwargs):
        """
        Condition method.
        """
        if self.expected_owner:
            return self.expected_owner.registrants.first()
        existing_account = zusers.find_account(args[0]['epp']['response']['resData']['infData']['email'].lower())
        if not existing_account:
            return False
#         existing_registrant = existing_account.registrants.first()
#         if not existing_registrant:
#             return False
#         if existing_registrant.epp_id != self.received_registrant_epp_id:
#             return False
        return True

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.domain_name = kwargs['domain_name']
        self.target_domain = zdomains.domain_find(domain_name=self.domain_name)
        self.change_owner_allowed = kwargs.get('change_owner_allowed', False)
        self.create_new_owner_allowed = kwargs.get('create_new_owner_allowed', False)
        self.refresh_contacts = kwargs.get('refresh_contacts', False)
        self.soft_delete = kwargs.get('soft_delete', True)
        self.domain_transferred_away = kwargs.get('domain_transferred_away', False)
        self.expected_owner = None
        self.rewrite_contacts = kwargs.get('rewrite_contacts', None)
        pending_order_items = orders.find_pending_domain_transfer_order_items(domain_name=self.domain_name)
        if len(pending_order_items) > 1:
            logger.critical('found more than one pending order for domain %s transfer: %r', self.domain_name, pending_order_items)
        if len(pending_order_items) > 0:
            related_order_item = pending_order_items[0]
            self.expected_owner = related_order_item.order.owner
            if 'rewrite_contacts' in related_order_item.details:
                if self.rewrite_contacts is None:
                    self.rewrite_contacts = related_order_item.details['rewrite_contacts']
            logger.info('found expected owner from one pending order %r : %r rewrite_contacts=%r',
                         related_order_item, self.expected_owner, self.rewrite_contacts)
        else:
            logger.info('no pending orders for %r', self.domain_name)
        logger.info('domain_refresher() started for %r with change_owner_allowed=%r create_new_owner_allowed=%r refresh_contacts=%r rewrite_contacts=%r',
                    self.target_domain, self.change_owner_allowed, self.create_new_owner_allowed, self.refresh_contacts, self.rewrite_contacts)

    def doEppDomainCheck(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_domain_check(
                domains=[self.domain_name, ],
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainCheck: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doEppDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_domain_info(
                domain=self.domain_name,
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', exc)
            return

        # catch "2201 Authorization error" result, that means domain exists, but have another owner
        try:
            code = int(response['epp']['response']['result']['@code'])
        except (ValueError, IndexError, TypeError, ) as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', exc)
            return

        if code == 2201:
            self.domain_info_response = response
            self.event('response', response)
            return

        # check create/expire date
        try:
            datetime.datetime.strptime(
                response['epp']['response']['resData']['infData']['exDate'],
                '%Y-%m-%dT%H:%M:%S.%fZ',
            )
            datetime.datetime.strptime(
                response['epp']['response']['resData']['infData']['crDate'],
                '%Y-%m-%dT%H:%M:%S.%fZ',
            )
        except Exception as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            raise rpc_error.EPPBadResponse('response field not recognized')

        # detect current nameservers
        try:
            current_nameservers = response['epp']['response']['resData']['infData']['ns']['hostObj']
        except:
            current_nameservers = []
        if not isinstance(current_nameservers, list):
            current_nameservers = [current_nameservers, ]
        self.received_nameservers = current_nameservers

        # detect current contacts
        try:
            current_contacts = response['epp']['response']['resData']['infData']['contact']
        except:
            current_contacts = []
        if not isinstance(current_contacts, list):
            current_contacts = [current_contacts, ]
        self.received_contacts = [{
            'type': i['@type'],
            'id': i['#text'],
        } for i in current_contacts]
        self.new_domain_contacts = {i['@type']:i['#text'] for i in current_contacts}

        # compare known contacts we have in DB with contacts received from back-end
        if not self.target_domain:
            self.contacts_changed = True
        else:
            if not self.refresh_contacts:
                add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
                    domain_object=self.target_domain,
                    domain_info_response=response,
                )
                if add_contacts or remove_contacts or change_registrant:
                    self.contacts_changed = True

        # detect current registrant
        try:
            self.received_registrant_epp_id = response['epp']['response']['resData']['infData']['registrant']
        except Exception as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', zerrors.RegistrantUnknown(response=response))
            return

        self.domain_info_response = response

        if self.expected_owner:
            # if pending order exists, select registrant from the owner of that order
            self.known_registrant = self.expected_owner.registrants.first()
            if self.known_registrant and self.known_registrant.epp_id:
                self.received_registrant_epp_id = self.known_registrant.epp_id
            logger.info('trying to use registrant from existing owner: %r', self.known_registrant)
        else:
            # find registrant in local DB
            self.known_registrant = zcontacts.registrant_find(epp_id=self.received_registrant_epp_id)
            logger.info('trying to find registrant by epp id %r: %r',
                        self.received_registrant_epp_id, self.known_registrant)

        if self.rewrite_contacts and self.known_registrant:
            logger.info('going to rewrite domain %r contacts from existing owner %r', self.domain_name, self.known_registrant.owner)
            self.event('rewrite-contacts', response)
            return

        if self.known_registrant:
            logger.info('registrant for domain %r is known: %r', self.domain_name, self.known_registrant)
            self.event('response', response)
            return

        if not self.create_new_owner_allowed:
            if self.domain_transferred_away:
                logger.error('domain %r is marked as transferred away', self.domain_name)
                self.event('domain-transferred-away')
            else:
                # fail if registrant not exist in local DB
                # that means owner of the domain changed, or his contact is not in sync with back-end
                # this also happens when domain is transferred to Zenaida, but user account not exist yet
                logger.error('registrant %r not exist in local DB', self.received_registrant_epp_id)
                self.event('error', zerrors.RegistrantAuthFailed('registrant not exist in local DB'))
            return

        # currently registrant not exist in local DB, user account needs to be checked and created first
        logger.info('registrant not exist in local DB, going to create new registrant')
        self.event('registrant-unknown', response)

    def doEppContactsInfoMany(self, *args, **kwargs):
        """
        Action method.
        """
        received_contacts_info = {}
        # request info about contacts
        for received_contact in self.received_contacts:
            try:
                response = rpc_client.cmd_contact_info(
                    contact_id=received_contact['id'],
                    raise_for_result=True,
                )
            except rpc_error.EPPError as exc:
                self.log(self.debug_level, 'Exception in doEPPContactsInfoMany: %s' % exc)
                self.event('error', exc)
                return
            received_contacts_info[received_contact['type']] = {
                'id': received_contact['id'],
                'response': response,
            }
        # request registrant info
        try:
            response = rpc_client.cmd_contact_info(
                contact_id=self.received_registrant_epp_id,
                raise_for_result=True,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEPPContactsInfoMany: %s' % exc)
            self.event('error', exc)
        else:
            received_contacts_info['registrant'] = {
                'id': self.received_registrant_epp_id,
                'response': response,
            }
            self.event('all-contacts-received', received_contacts_info)

    def doEppCurrentRegistrantInfo(self, *args, **kwargs):
        """
        Action method.
        """
        # request current registrant info
        try:
            response = rpc_client.cmd_contact_info(
                contact_id=self.received_registrant_epp_id,
                raise_for_result=True,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppCurrentRegistrantInfo: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            if self.rewrite_contacts and self.new_domain_contacts:
                to_be_added = self.contacts_to_add or [{'type': role, 'id': epp_id, } for role, epp_id in self.new_domain_contacts.items()]
                to_be_removed = self.contacts_to_remove or self.received_contacts
                add_contacts_list, remove_contacts_list = zcontacts.clear_contacts_change(to_be_added, to_be_removed)
                response = rpc_client.cmd_domain_update(
                    domain=self.domain_name,
                    change_registrant=self.new_registrant_epp_id,
                    remove_contacts_list=remove_contacts_list,
                    add_contacts_list=add_contacts_list,
                )
            else:
                response = rpc_client.cmd_domain_update(
                    domain=self.domain_name,
                    change_registrant=self.new_registrant_epp_id,
                )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainUpdate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doUseExistingRegistrant(self, *args, **kwargs):
        """
        Action method.
        """
        response = args[0]
        self.latest_registrant_response = response
        self.current_registrant_info = response['epp']['response']['resData']['infData']
        self.current_registrant_address_info = zcontacts.extract_address_info(response)
        existing_account = zusers.find_account(self.current_registrant_info['email'].lower())
        self.new_registrant_epp_id = existing_account.registrants.first().epp_id

    def doUseReceivedRegistrantInfo(self, *args, **kwargs):
        """
        Action method.
        """
        response = args[0]
        self.latest_registrant_response = response
        self.current_registrant_info = response['epp']['response']['resData']['infData']
        self.current_registrant_address_info = zcontacts.extract_address_info(response)
        self.new_registrant_epp_id = self.received_registrant_epp_id

    def doUseExistingContacts(self, *args, **kwargs):
        """
        Action method.
        """
        self.new_registrant_epp_id = self.known_registrant.epp_id
        first_contact = self.known_registrant.owner.contacts.first()
        if not first_contact:
            first_contact = zcontacts.contact_create_from_profile(self.known_registrant.owner, self.known_registrant.owner.profile)
        if first_contact.epp_id:
            if not self.new_domain_contacts.get('admin'):
                self.new_domain_contacts['admin'] = first_contact.epp_id
        if self.target_domain:
            self.contacts_to_add, self.contacts_to_remove, _ = zdomains.compare_contacts(
                domain_object=self.target_domain,
                domain_info_response=self.domain_info_response,
                target_contacts=list({
                    'admin': first_contact,
                    'billing': first_contact,
                    'tech': first_contact,
                }.items()),
            )

    def doRewriteDomainContacts(self, *args, **kwargs):
        """
        Action method.
        """
        dcs = domain_contacts_synchronizer.DomainContactsSynchronizer(
            update_domain=False,
            skip_roles=['registrant', ],
            skip_contact_details=False,
            merge_duplicated_contacts=False,
            raise_errors=True,
            accept_code_2304=False,
        )
        try:
            dcs.event('run', target_domain=self.target_domain, )
        except Exception as exc:
            self.log(self.debug_level, 'Exception in DomainContactsSynchronizer: %s' % exc)
            del dcs
            self.event('contacts-rewrite-error', exc)
            return
        outputs = list(dcs.outputs)
        del dcs
        if not outputs:
            logger.error('empty result from DomainContactsSynchronizer: %s', exc)
            self.event('contacts-rewrite-error', Exception('Empty result from DomainContactsSynchronizer'))
            return
        if isinstance(outputs[-1], Exception):
            logger.error('found exception in DomainContactsSynchronizer outputs: %s', outputs[-1])
            self.event('contacts-rewrite-error', outputs[-1])
            return
        for out in outputs:
            if not isinstance(out, tuple):
                continue
            if not out[0] in ['admin', 'billing', 'tech', 'registrant', ]:
                logger.warn('unexpected output from DomainContactsSynchronizer: %r', out[0])
                continue
        self.outputs.extend(outputs)
        self.event('contacts-replaced', self.latest_registrant_response)

    def doDBCheckCreateUserAccount(self, *args, **kwargs):
        """
        Action method.
        """
        if self.known_registrant:
            logger.info('registrant already known so skip creating user account')
            return
        known_owner = zusers.find_account(self.current_registrant_info['email'])
        if not known_owner:
            known_owner = zusers.create_account(
                email=self.current_registrant_info['email'],
                account_password=zusers.generate_password(length=10),
                also_profile=True,
                is_active=True,
                person_name=self.current_registrant_address_info.get('name', 'unknown'),
                organization_name=self.current_registrant_address_info.get('org', 'unknown'),
                address_street=self.current_registrant_address_info.get('street', 'unknown'),
                address_city=self.current_registrant_address_info.get('city', 'unknown'),
                address_province=self.current_registrant_address_info.get('sp', 'unknown'),
                address_postal_code=self.current_registrant_address_info.get('pc', 'unknown'),
                address_country=self.current_registrant_address_info.get('cc', 'AF'),
                contact_voice=zcontacts.extract_phone_number(self.current_registrant_info.get('voice', '')),
                contact_fax=zcontacts.extract_phone_number(self.current_registrant_info.get('fax', '')),
                contact_email=self.current_registrant_info['email'],
            )
        if not hasattr(known_owner, 'profile'):
            zusers.create_profile(
                known_owner,
                person_name=self.current_registrant_address_info.get('name', 'unknown'),
                organization_name=self.current_registrant_address_info.get('org', 'unknown'),
                address_street=self.current_registrant_address_info.get('street', 'unknown'),
                address_city=self.current_registrant_address_info.get('city', 'unknown'),
                address_province=self.current_registrant_address_info.get('sp', 'unknown'),
                address_postal_code=self.current_registrant_address_info.get('pc', 'unknown'),
                address_country=self.current_registrant_address_info.get('cc', 'AF'),
                contact_voice=zcontacts.extract_phone_number(self.current_registrant_info.get('voice', '')),
                contact_fax=zcontacts.extract_phone_number(self.current_registrant_info.get('fax', '')),
                contact_email=self.current_registrant_info['email'],
            )
        self.received_registrant_epp_id = self.new_registrant_epp_id
        self.known_registrant = zcontacts.registrant_find(epp_id=self.received_registrant_epp_id)
        if not self.known_registrant:
            logger.info('new registrant will be created for %r', known_owner)
            self.known_registrant = zcontacts.registrant_create_from_profile(
                owner=known_owner,
                profile_object=known_owner.profile,
                epp_id=self.received_registrant_epp_id,
            )
            if self.target_domain:
                zdomains.domain_detach_contact(self.target_domain, 'admin')
                zdomains.domain_detach_contact(self.target_domain, 'billing')
                zdomains.domain_detach_contact(self.target_domain, 'tech')
            self.new_domain_contacts.pop('admin', None)
            self.new_domain_contacts.pop('billing', None)
            self.new_domain_contacts.pop('tech', None)
        if self.target_domain:
            self.target_domain.refresh_from_db()

    def doDBSetDomainContacts(self, *args, **kwargs):
        """
        Action method.
        """
        first_contact = self.known_registrant.owner.contacts.first()
        if not first_contact:
            first_contact = zcontacts.contact_create_from_profile(self.known_registrant.owner, self.known_registrant.owner.profile)
        zdomains.domain_join_contact(self.target_domain, 'admin', first_contact)
        self.target_domain.refresh_from_db()

    def doDBDeleteDomain(self, *args, **kwargs):
        """
        Action method.
        """
        if self.soft_delete:
            zdomains.domain_unregister(domain_name=self.domain_name)
        else:
            zdomains.domain_delete(domain_name=self.domain_name)

    def doDBCheckCreateUpdateContacts(self, *args, **kwargs):
        """
        Action method.
        """
        if self.rewrite_contacts:
            # that indicates that we actually want to overwrite domain contacts on back-end
            if self.target_domain:
                # when domain exists - skip
                return
            first_contact = self.known_registrant.owner.contacts.first()
            if not first_contact:
                first_contact = zcontacts.contact_create_from_profile(self.known_registrant.owner, self.known_registrant.owner.profile)
            # only populate Admin contact from one of the existing contacts that must already exist!
            self.new_domain_contacts = {'admin': first_contact.epp_id, }
            return
        received_contacts_info = args[0]
        # even if domain not exist yet make sure all contacts really exists in DB and in sync with back-end
        for role in ['admin', 'billing', 'tech', ]:
            received_contact_id = received_contacts_info.get(role, {'id': None, })['id']
            if not received_contact_id:
                continue
            existing_contact = zcontacts.by_epp_id(epp_id=received_contact_id)
            if existing_contact:
                if existing_contact.owner != self.known_registrant.owner:
                    if self.change_owner_allowed:
                        continue
                    logger.error('existing contact have another owner in local DB')
                    self.event('error', zerrors.RegistrantAuthFailed('existing contact have another owner in local DB'))
                    return
                zcontacts.contact_refresh(
                    epp_id=received_contact_id,
                    contact_info_response=received_contacts_info[role]['response'],
                )
            else:
                zcontacts.contact_create(
                    epp_id=received_contact_id,
                    owner=self.known_registrant.owner,
                    contact_info_response=received_contacts_info[role]['response'],
                )

    def doDBCheckCreateDomain(self, *args, **kwargs):
        """
        Action method.
        """
        if self.target_domain:
            return
        self.target_domain = zdomains.domain_create(
            self.domain_name,
            owner=self.known_registrant.owner,
            expiry_date=zdomains.response_to_datetime('exDate', self.domain_info_response),
            create_date=zdomains.response_to_datetime('crDate', self.domain_info_response),
            epp_id=self.domain_info_response['epp']['response']['resData']['infData']['roid'],
            auth_key='',
            registrar=None,
            registrant=self.known_registrant,
            contact_admin=zcontacts.by_epp_id(self.new_domain_contacts.get('admin')) if self.new_domain_contacts.get('admin') else None,
            contact_tech=zcontacts.by_epp_id(self.new_domain_contacts.get('tech')) if self.new_domain_contacts.get('tech') else None,
            contact_billing=zcontacts.by_epp_id(self.new_domain_contacts.get('billing')) if self.new_domain_contacts.get('billing') else None,
            nameservers=self.received_nameservers,
            save=True,
        )

    def doDBCheckChangeOwner(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.target_domain:
            return
        # update registrant of the domain if it is known
        if self.target_domain.registrant and self.known_registrant and self.target_domain.registrant != self.known_registrant:
            if not self.change_owner_allowed:
                logger.error('domain registrant changed, but domain already have another owner in local DB')
                raise zerrors.RegistrantAuthFailed('domain registrant changed, but domain already have another owner in local DB')
            logger.info('domain %r going to switch registrant %r to %r',
                        self.target_domain, self.target_domain.registrant, self.known_registrant)
            self.target_domain = zdomains.domain_change_registrant(self.target_domain, self.known_registrant)
            self.target_domain.refresh_from_db()
            first_contact = self.known_registrant.owner.contacts.first()
            self.target_domain = zdomains.domain_replace_contacts(self.target_domain, new_admin_contact=first_contact)
            self.target_domain.refresh_from_db()
            return
        # make sure owner of the domain is correct
        if self.known_registrant and self.target_domain.owner != self.known_registrant.owner:
            # just in case given user have multiple registrant contacts... 
            if not self.change_owner_allowed:
                logger.error('domain already have another owner in local DB')
                raise zerrors.RegistrantAuthFailed('domain already have another owner in local DB')
            logger.info('domain %r going to switch owner %r to %r because of different registrant found',
                        self.target_domain, self.target_domain.owner, self.known_registrant.owner)
            self.target_domain = zdomains.domain_change_owner(self.target_domain, self.known_registrant.owner)
            self.target_domain.refresh_from_db()
            first_contact = self.known_registrant.owner.contacts.first()
            self.target_domain = zdomains.domain_replace_contacts(self.target_domain, new_admin_contact=first_contact)
            self.target_domain.refresh_from_db()
            return
        # also check if registrant's email changed on back-end
        # in that situation new account needs to be created and all domains and contacts re-attached to the new account
        # this must be done separately, because that flow is only focused on single domain object
        try:
            received_registrant_email = args[0]['registrant']['response']['epp']['response']['resData']['infData']['email'].lower()
        except:
            received_registrant_email = self.target_domain.registrant.contact_email.lower()
        if received_registrant_email != self.target_domain.registrant.contact_email.lower():
            existing_registrant = zcontacts.registrant_find(contact_email=received_registrant_email)
            if existing_registrant:
                logger.error('registrant %r contact email changed to %r, but another registrant with same email already exist in local DB: %r',
                             self.target_domain.registrant, received_registrant_email, existing_registrant)
                raise zerrors.RegistrantAuthFailed('registrant contact email changed, but another registrant with same email already exist in local DB')
            existing_account = zusers.find_account(email=received_registrant_email)
            if existing_account:
                logger.error('registrant %r contact email changed to %r, but another account already exist in local DB with same email: %r',
                             self.target_domain.registrant, received_registrant_email, existing_registrant)
                raise zerrors.RegistrantAuthFailed('registrant contact email changed, but another account already exist in local DB with same email')
            logger.error('registrant %r contact email changed to %s and needs to be synchronized', self.target_domain.registrant, received_registrant_email)
            raise zerrors.RegistrantAuthFailed('registrant contact email changed and needs to be synchronized')

    def doDBCheckChangeContacts(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.target_domain:
            return
        if self.rewrite_contacts or self.change_owner_allowed:
            return
        received_contacts_info = args[0]
        for role in ['admin', 'billing', 'tech', ]:
            received_contact_id = received_contacts_info.get(role, {'id': None, })['id']
            known_contact_id = None
            known_contact = self.target_domain.get_contact(role)
            if known_contact:
                known_contact_id = known_contact.epp_id
            if not received_contact_id and not known_contact_id:
                continue
            if not received_contact_id:
                logger.info('domain %r going to remove existing contact %s', self.target_domain, role)
                zdomains.domain_detach_contact(self.target_domain, role)
                self.target_domain.refresh_from_db()
                continue
            new_contact = zcontacts.by_epp_id(received_contact_id)
            if not new_contact:
                raise Exception('can not assign contact to domain, epp_id not found')
            if not known_contact_id:
                logger.info('domain %r going to add new contact %s : %r',
                            self.target_domain, role, self.known_registrant.owner)
                zdomains.domain_join_contact(self.target_domain, role, new_contact)
                self.target_domain.refresh_from_db()
                continue
            if received_contact_id != known_contact_id:
                logger.info('domain %r going to switch contact %s : from %r to %r',
                            self.target_domain, role, known_contact, new_contact)
                zdomains.domain_join_contact(self.target_domain, role, new_contact)
                self.target_domain.refresh_from_db()
                continue
            logger.info('domain %r current %s contact in sync', self.target_domain, role)

    def doDBCheckUpdateNameservers(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.target_domain:
            return
        zdomains.update_nameservers(
            domain_object=self.target_domain,
            domain_info_response=self.domain_info_response,
        )
        self.target_domain.refresh_from_db()

    def doDBCheckUpdateDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.target_domain:
            return
        self.target_domain.expiry_date=zdomains.response_to_datetime('exDate', self.domain_info_response)
        self.target_domain.create_date=zdomains.response_to_datetime('crDate', self.domain_info_response)
        self.target_domain.save()
        zdomains.domain_update_statuses(self.target_domain, self.domain_info_response)
        self.target_domain.refresh_from_db()

    def doCheckProcessPendingOrder(self, *args, **kwargs):
        """
        Action method.
        """
        pending_order_items = orders.find_pending_domain_transfer_order_items(domain_name=self.domain_name)
        if len(pending_order_items) > 1:
            logger.critical('found more than one pending order for domain %s transfer: %r', self.domain_name, pending_order_items)
        if len(pending_order_items) > 0:
            related_order_item = pending_order_items[0]
            orders.update_order_item(related_order_item, new_status='processed', charge_user=True, save=True)
            orders.refresh_order(related_order_item.order)
            logger.info('processed one pending order %r for %r', related_order_item, self.expected_owner)
        else:
            logger.info('no pending orders found for %r', self.domain_name)

    def doReportNotExist(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(None)

    def doReportAnotherRegistrar(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(None)

    def doReportCheckFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportInfoFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportDomainInfo(self, *args, **kwargs):
        """
        Action method.
        """
        if self.target_domain:
            zdomains.domain_update_statuses(
                domain_object=self.target_domain,
                domain_info_response=args[0],
            )
            self.target_domain.refresh_from_db()
        self.outputs.append(args[0])

    def doReportContactsFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportCurRegistrantFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportNewRegistrantFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportDomainUpdateFailed(self, event, *args, **kwargs):
        """
        Action method.
        """
        if event == 'error':
            self.outputs.append(args[0])
        else:
            self.outputs.append(rpc_error.exception_from_response(response=args[0]))

    def doReportContactsInfo(self, *args, **kwargs):
        """
        Action method.
        """
        received_contacts_info = args[0] 
        for role, response in received_contacts_info.items():
            self.outputs.append(response['response'])

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.expected_owner = None
        self.soft_delete = None
        self.domain_transferred_away = None
        self.change_owner_allowed = None
        self.create_new_owner_allowed = None
        self.domain_name = None
        self.target_domain = None
        self.contacts_changed = False
        self.domain_info_response = None
        self.received_contacts = []
        self.new_domain_contacts = {}
        self.received_nameservers = []
        self.new_registrant_epp_id = None
        self.current_registrant_info = None
        self.current_registrant_address_info = None
        self.contacts_to_add = None
        self.contacts_to_remove = None
        self.latest_registrant_response = None
        self.destroy()
