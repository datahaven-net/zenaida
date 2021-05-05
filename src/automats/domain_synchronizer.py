#!/usr/bin/env python
# domain_synchronizer.py

"""
.. module:: domain_synchronizer
.. role:: red

Zenaida domain_synchronizer() Automat

EVENTS:
    * :red:`contacts-ok`
    * :red:`error`
    * :red:`nameservers-ok`
    * :red:`no-updates`
    * :red:`response`
    * :red:`run`
"""

#------------------------------------------------------------------------------

import logging
import datetime

from django.conf import settings
from django.utils import timezone

#------------------------------------------------------------------------------

from automats import automat
from automats import domain_contacts_synchronizer
from automats import domain_hostnames_synchronizer

from epp import rpc_client
from epp import rpc_error

from zen import zdomains
from zen import zerrors

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``domain_synchronizer()`` state machine.
    """

    def __init__(self, debug_level=4, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domain_synchronizer()` state machine.
        """
        self.target_domain = None
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        self.accept_code_2304 = kwargs.pop('accept_code_2304', True)
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

    @property
    def label(self):
        if not self.target_domain:
            return '%s(%s)' % (self.id, self.state)
        return '%s[%s](%s)' % (self.id, self.target_domain.name, self.state)

    def init(self):
        """
        Method to initialize additional variables and flags
        at creation phase of `domain_synchronizer()` machine.
        """
        self.latest_domain_info = None

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
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'EXISTS?'
                self.doInit(*args, **kwargs)
                self.doEppDomainCheck(*args, **kwargs)
        #---EXISTS?---
        elif self.state == 'EXISTS?':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isDomainExist(*args, **kwargs):
                self.state = 'CONTACTS'
                self.DomainToBeCreated=True
                self.doRunDomainContactsSync(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and self.isDomainExist(*args, **kwargs):
                self.state = 'OWNER?'
                self.DomainToBeCreated=False
                self.doEppDomainInfo(*args, **kwargs)
        #---OWNER?---
        elif self.state == 'OWNER?':
            if event == 'error' or ( event == 'response' and not self.isCode(2201, *args, **kwargs) and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(2201, *args, **kwargs):
                self.state = 'FAILED'
                self.doReportAnotherOwner(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'CONTACTS'
                self.doRunDomainContactsSync(*args, **kwargs)
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
            if event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'nameservers-ok' and not self.DomainToBeCreated:
                self.state = 'READ'
                self.doEppDomainInfo(*args, **kwargs)
            elif event == 'nameservers-ok' and self.DomainToBeCreated:
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
                self.doDBWriteDomainCreated(*args, **kwargs)
                self.doReportCreated(event, *args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
        #---READ---
        elif self.state == 'READ':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'UPDATE!'
                self.doDBWriteDomainEPPId(*args, **kwargs)
                self.doEppDomainUpdate(*args, **kwargs)
        #---UPDATE!---
        elif self.state == 'UPDATE!':
            if event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif ( event == 'no-updates' or ( event == 'response' and self.isCode(1000, *args, **kwargs) ) ) and not self.isDomainToBeRenew(*args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif ( event == 'no-updates' or ( event == 'response' and self.isCode(1000, *args, **kwargs) ) ) and self.isDomainToBeRenew(*args, **kwargs):
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
                self.doDBWriteDomainRenew(*args, **kwargs)
                self.doReportRenew(*args, **kwargs)
                self.doReportDone(event, *args, **kwargs)
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

    def isDomainExist(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0]['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '0'

    def isDomainToBeRenew(self, *args, **kwargs):
        """
        Condition method.
        """
        return self.renew_years is not None and not self.DomainToBeCreated

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_domain = args[0]
        self.renew_years = kwargs.get('renew_years', None)
        self.sync_contacts = kwargs.get('sync_contacts', True)
        self.sync_nameservers = kwargs.get('sync_nameservers', True)
        self.save_to_db = kwargs.get('save_to_db', True)

    def doEppDomainCheck(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_domain_check(
                domains=[self.target_domain.name, ],
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
                domain=self.target_domain.name,
                auth_info=self.target_domain.auth_key or None,
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainInfo: %s' % exc)
            self.event('error', exc)
        else:
            self.latest_domain_info = response
            self.event('response', response)

    def doEppDomainCreate(self, *args, **kwargs):
        """
        Action method.
        """
        if self.renew_years == -1 or self.renew_years is None:
            # initial load scenario
            days_difference = (self.target_domain.expiry_date - timezone.now()).days
        else:
            days_difference = 365 * self.renew_years
        if days_difference > 365 * 10 - 1:
            logger.error('extension period must be no more than 10 years: %s', self.target_domain)
            self.event('error', Exception('extension period must be no more than 10 years'))
            return
        if days_difference % 365 == 0:
            period_units = 'y'
            period_value = str(int(days_difference / 365.0))
        else:
            period_units = 'd'
            period_value = str(days_difference)
        contacts_dict = {}
        for role, contact_object in self.target_domain.list_contacts():
            if contact_object:
                contacts_dict[role] = contact_object.epp_id
        try:
            response = rpc_client.cmd_domain_create(
                domain=self.target_domain.name,
                nameservers=self.target_domain.list_nameservers(),
                contacts_dict=contacts_dict,
                registrant=self.target_domain.registrant.epp_id,
                period=period_value,
                period_units=period_units,
            )
            # TODO: 
            # epp_domain_info['svTRID'] = create['epp']['response']['trID']['svTRID']
            # epp_domain_info['crDate'] = create['epp']['response']['resData']['creData']['crDate']
            # epp_domain_info['exDate'] = create['epp']['response']['resData']['creData']['exDate']
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainCreate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        add_contacts, remove_contacts, change_registrant = zdomains.compare_contacts(
            domain_object=self.target_domain,
            domain_info_response=args[0],
        )
        add_nameservers, remove_nameservers = zdomains.compare_nameservers(
            domain_object=self.target_domain,
            domain_info_response=args[0],
        )
        if not (add_contacts or remove_contacts or add_nameservers or remove_nameservers or change_registrant):
            self.event('no-updates')
            return
        try:
            response = rpc_client.cmd_domain_update(
                domain=self.target_domain.name,
                change_registrant=change_registrant,
                add_contacts_list=add_contacts,
                remove_contacts_list=remove_contacts,
                add_nameservers_list=add_nameservers,
                remove_nameservers_list=remove_nameservers,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainUpdate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doEppDomainRenew(self, *args, **kwargs):
        """
        Action method.
        """
        if self.renew_years == -1 or self.renew_years is None:
            # initial load scenario
            days_difference = (self.target_domain.expiry_date - timezone.now()).days
        else:
            days_difference = 365 * self.renew_years
        if days_difference > 365 * 10 - 1:
            logger.error('extension period must be no more than 10 years: %s', self.target_domain)
            self.event('error', Exception('extension period must be no more than 10 years'))
            return
        if days_difference % 365 == 0:
            period_units = 'y'
            period_value = str(int(days_difference / 365.0))
        else:
            period_units = 'd'
            period_value = str(days_difference)
        try:
            response = rpc_client.cmd_domain_renew(
                domain=self.target_domain.name,
                cur_exp_date=self.latest_domain_info['epp']['response']['resData']['infData']['exDate'],
                period=period_value,
                period_units=period_units,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainRenew: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doRunDomainContactsSync(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.sync_contacts:
            self.event('contacts-ok')
            return
        dcs = domain_contacts_synchronizer.DomainContactsSynchronizer(
            update_domain=False,
            skip_roles=[],
            skip_contact_details=(not self.DomainToBeCreated),
            raise_errors=True,
            accept_code_2304=self.accept_code_2304,
        )
        try:
            dcs.event('run', target_domain=self.target_domain, )
        except Exception as exc:
            self.log(self.debug_level, 'Exception in DomainContactsSynchronizer: %s' % exc)
            del dcs
            self.event('error', exc)
            return
        outputs = list(dcs.outputs)
        del dcs
        if not outputs:
            logger.error('empty result from DomainContactsSynchronizer: %s', exc)
            self.event('error', Exception('Empty result from DomainContactsSynchronizer'))
            return
        if isinstance(outputs[-1], Exception):
            logger.error('found exception in DomainContactsSynchronizer outputs: %s', outputs[-1])
            self.event('error', outputs[-1])
            return
        for out in outputs:
            if not isinstance(out, tuple):
                continue
            if not out[0] in ['admin', 'billing', 'tech', 'registrant', ]:
                logger.warn('unexpected output from DomainContactsSynchronizer: %r', out[0])
                continue
        self.outputs.extend(outputs)
        self.event('contacts-ok')

    def doRunDomainNameserversSync(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.sync_nameservers:
            self.event('nameservers-ok')
            return
        dhs = domain_hostnames_synchronizer.DomainHostnamesSynchronizer(
            update_domain=False,  # (not self.DomainToBeCreated),
            raise_errors=True,
        )
        try:
            dhs.event('run', target_domain=self.target_domain, known_domain_info=self.latest_domain_info, )
        except Exception as exc:
            self.log(self.debug_level, 'Exception in DomainHostnamesSynchronizer: %s' % exc)
            del dhs
            self.event('error', exc)
            return
        self.outputs.extend(list(dhs.outputs))
        del dhs
        self.event('nameservers-ok')
        
    def doDBWriteDomainCreated(self, *args, **kwargs):
        """
        Action method.
        """
        # TODO: args[0]['epp']['response']['trID']['svTRID']  store in history
        self.target_domain.create_date = datetime.datetime.strptime(
            args[0]['epp']['response']['resData']['creData']['crDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        self.target_domain.expiry_date = datetime.datetime.strptime(
            args[0]['epp']['response']['resData']['creData']['exDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        self.target_domain.status = 'active'
        if self.save_to_db:
            self.target_domain.save()

    def doDBWriteDomainRenew(self, *args, **kwargs):
        """
        Action method.
        """
        # TODO: args[0]['epp']['response']['trID']['svTRID']  store in history
        self.target_domain.expiry_date = datetime.datetime.strptime(
            args[0]['epp']['response']['resData']['renData']['exDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if self.save_to_db:
            self.target_domain.save()

    def doDBWriteDomainEPPId(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_domain.epp_id = args[0]['epp']['response']['resData']['infData']['roid']
        if self.save_to_db:
            self.target_domain.save()
        zdomains.domain_update_statuses(
            domain_object=self.target_domain,
            domain_info_response=args[0],
            save=self.save_to_db,
        )

    def doReportDone(self, event, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(True)

    def doReportCreated(self, event, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(args[0])

    def doReportRenew(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(args[0])

    def doReportAnotherOwner(self, *args, **kwargs):
        """
        Action method.
        """
        self.outputs.append(zerrors.RegistrarAuthFailed(response=args[0]))

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
        self.target_domain = None
        self.renew_years = None
        self.sync_contacts = None
        self.sync_nameservers = None
        self.verify_owner = None
        self.latest_domain_info = None
        self.destroy()

