#!/usr/bin/env python
# domain_reader.py

"""
.. module:: domain_reader
.. role:: red

Zenaida domain_reader() Automat

EVENTS:
    * :red:`all-contacts-ok`
    * :red:`error`
    * :red:`response`
    * :red:`run`
"""

#------------------------------------------------------------------------------

import logging
import time
import datetime

from django.conf import settings

from email.utils import formatdate

#------------------------------------------------------------------------------

from automats import automat

from epp import rpc_client
from epp import rpc_error

from zen import zdomains
from zen import zerrors

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainReader(automat.Automat):
    """
    This class implements all the functionality of ``domain_reader()`` state machine.
    """

    def __init__(self, verify_registrant=True, debug_level=4, log_events=False, log_transitions=False, raise_errors=False, **kwargs):
        """
        Builds `domain_reader()` state machine.
        """
        self.target_domain = None
        self.verify_registrant = verify_registrant
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainReader, self).__init__(
            name="domain_reader",
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
        at creation phase of `domain_reader()` machine.
        """

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Method to catch the moment when `domain_reader()` state were changed.
        """

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        This method intended to catch the moment when some event was fired in the `domain_reader()`
        but automat state was not changed.
        """

    def A(self, event, *args, **kwargs):
        """
        The state machine code, generated using `visio2python <http://bitdust.io/visio2python/>`_ tool.
        """
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run':
                self.state = 'DOMAIN_INFO'
                self.doInit(*args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
        #---DOMAIN_INFO---
        elif self.state == 'DOMAIN_INFO':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'CONTACTS_INFO'
                self.doVerifyRegistrant(*args, **kwargs)
                self.doPrepareContactsList(*args, **kwargs)
                self.doEppContactInfoMany(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---CONTACTS_INFO---
        elif self.state == 'CONTACTS_INFO':
            if event == 'all-contacts-ok':
                self.state = 'REGISTRANT_INFO'
                self.doEppContactInfoRegistrant(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---REGISTRANT_INFO---
        elif self.state == 'REGISTRANT_INFO':
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
        #---FAILED---
        elif self.state == 'FAILED':
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
        self.result = {}

    def doVerifyRegistrant(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.verify_registrant:
            return
        self.registrant_epp_id = args[0]['epp']['response']['resData']['infData'].get('registrant', None)
        if not self.registrant_epp_id:
            logger.error('domain registrant unknown from response: %s', self.target_domain.name)
            self.event('error', zerrors.RegistrantUnknown(response=args[0]))
            return
        known_domain = zdomains.domain_find(domain_name=self.target_domain.name)
        if not known_domain:
            return
        if known_domain.registrant.epp_id == self.registrant_epp_id:
            return
        logger.error('domain known to belong to another registrant: %s', self.current_domain_name)
        self.event('error', zerrors.RegistrantAuthFailed(response=args[0]))

    def doPrepareContactsList(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response_contacts = args[0]['epp']['response']['resData']['infData']['contact']
        except:
            response_contacts = []
        if not isinstance(response_contacts, list):
            response_contacts = [response_contacts, ]
        self.domain_contacts = [{'type': i['@type'], 'id': i['#text']} for i in response_contacts]
        self.result.update({
            'name': args[0]['epp']['response']['resData']['infData']['name'],
            'roid': str(args[0]['epp']['response']['resData']['infData']['roid']),
            'crDate': self._date_transform(args[0]['epp']['response']['resData']['infData'].get('crDate', '')),
            'upDate': self._date_transform(args[0]['epp']['response']['resData']['infData'].get('upDate', '')),
            'exDate': self._date_transform(args[0]['epp']['response']['resData']['infData'].get('exDate', '')),
            'admin': {},
            'tech': {},
            'billing': {},
            'registrant': {},
            'hostnames': [],
        })

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
            self.event('response', response)

    def doEppContactInfoMany(self, *args, **kwargs):
        """
        Action method.
        """
        for contact in self.domain_contacts:
            try:
                response = rpc_client.cmd_contact_info(
                    contact_id=contact['id'],
                    raise_for_result=False,
                )
                response_code = int(args[1]['epp']['response']['result']['@code'])
            except rpc_error.EPPError as exc:
                self.log(self.debug_level, 'Exception in doEppContactInfoMany: %s' % exc)
                self.event('error', exc)
                return
            self.event('response', response)
            if response_code != 1000:
                return
            d = response['epp']['response']['resData']['infData']
            self.result[contact['type']] = {
                'id': str(d['id']),
                'email': str(d['email']).lower(),
                'voice': str(d.get('voice', '')),
                'fax': str(d.get('fax', '')),
            }
            postal_info_list = d['postalInfo'] if isinstance(d['postalInfo'], list) else [d['postalInfo'], ]
            local_address = False
            for postal_info in postal_info_list:
                if postal_info['@type'] == 'loc':
                    local_address = True
                    self.result[contact['type']].update(self._extract_postal_info(postal_info))
                    break
            if not local_address:
                for postal_info in postal_info_list:
                    self.result[contact['type']].update(self._extract_postal_info(postal_info))
        self.event('all-contacts-ok')

    def doEppContactInfoRegistrant(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            response = rpc_client.cmd_contact_info(
                contact_id=self.registrant_epp_id,
                raise_for_result=False,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppContactInfoRegistrant: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', response)

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """

    def doReportFailed(self, event, *args, **kwargs):
        """
        Action method.
        """

    def doDestroyMe(self, *args, **kwargs):
        """
        Remove all references to the state machine object to destroy it.
        """
        self.destroy()

    def _date_transform(self, epp_date):
        if not epp_date:
            return ''
        return formatdate(time.mktime(datetime.datetime.strptime(
            epp_date, '%Y-%m-%dT%H:%M:%S.%fZ').timetuple()), True)

    def _extract_postal_info(self, pi):
        return {
            'name': pi.get('name', ''),
            'org': pi.get('org', ''),
            'cc': pi.get('addr', {}).get('cc'),
            'city': pi.get('addr', {}).get('city'),
            'pc': pi.get('addr', {}).get('pc'),
            'sp': pi.get('addr', {}).get('sp'),
            'street': (' '.join(pi.get('addr', {}).get('street'))) if isinstance(
                pi.get('addr', {}).get('street'), list) else pi.get('addr', {}).get('street'),
        }
