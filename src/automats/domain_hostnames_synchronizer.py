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
    * :red:`no-hosts-to-be-added`
    * :red:`response`
    * :red:`run`
"""


#------------------------------------------------------------------------------

import logging

from django.conf import settings

#------------------------------------------------------------------------------

from automats import automat

from epp import rpc_client
from epp import rpc_error

from zen import zdomains

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class DomainHostnamesSynchronizer(automat.Automat):
    """
    This class implements all the functionality of ``domain_hostnames_synchronizer()`` state machine.
    """

    def __init__(self, update_domain=True,
                 debug_level=4, log_events=None, log_transitions=None,
                 raise_errors=False, **kwargs):
        """
        Builds `domain_hostnames_synchronizer()` state machine.
        """
        self.target_domain = None
        self.update_domain = update_domain
        if log_events is None:
            log_events=settings.DEBUG
        if log_transitions is None:
            log_transitions=settings.DEBUG
        super(DomainHostnamesSynchronizer, self).__init__(
            name="domain_hostnames_synchronizer",
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
        at creation phase of `domain_hostnames_synchronizer()` machine.
        """
        self.known_domain_info = None

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
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'run' and not self.isUpdateRequired(*args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'run' and self.isExisting(*args, **kwargs) and self.isUpdateRequired(*args, **kwargs):
                self.state = 'DOMAIN_INFO?'
                self.doInit(*args, **kwargs)
                self.doEppDomainInfo(*args, **kwargs)
            elif event == 'run' and not self.isExisting(*args, **kwargs) and self.isUpdateRequired(*args, **kwargs):
                self.state = 'HOSTS_CHECK'
                self.doInit(*args, **kwargs)
                self.doPrepareHosts(*args, **kwargs)
                self.doEppHostCheckMany(*args, **kwargs)
        #---DOMAIN_INFO?---
        elif self.state == 'DOMAIN_INFO?':
            if event == 'response' and self.isCode(1000, *args, **kwargs) and not self.isUpdateRequired(*args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'response' and self.isCode(1000, *args, **kwargs) and self.isUpdateRequired(*args, **kwargs):
                self.state = 'HOSTS_CHECK'
                self.doPrepareHosts(*args, **kwargs)
                self.doEppHostCheckMany(*args, **kwargs)
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
            if event == 'error':
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'all-hosts-created' and self.isDomainUpdateNow(*args, **kwargs):
                self.state = 'DOMAIN_UPDATE!'
                self.doEppDomainUpdate(*args, **kwargs)
            elif event == 'all-hosts-created' and not self.isDomainUpdateNow(*args, **kwargs):
                self.state = 'DONE'
                self.doReportDone(*args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
        #---DONE---
        elif self.state == 'DONE':
            pass
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        #---HOSTS_CHECK---
        elif self.state == 'HOSTS_CHECK':
            if event == 'response' and self.isCode(1000, *args, **kwargs):
                self.state = 'HOSTS_CREATE'
                self.doEppHostCreateMany(*args, **kwargs)
            elif event == 'error' or ( event == 'response' and not self.isCode(1000, *args, **kwargs) ):
                self.state = 'FAILED'
                self.doReportFailed(event, *args, **kwargs)
                self.doDestroyMe(*args, **kwargs)
            elif event == 'no-hosts-to-be-added':
                self.state = 'DOMAIN_UPDATE!'
                self.doEppDomainUpdate(*args, **kwargs)
        return None

    def isCode(self, *args, **kwargs):
        """
        Condition method.
        """
        return args[0] == int(args[1]['epp']['response']['result']['@code'])

    def isExisting(self, *args, **kwargs):
        """
        Condition method.
        """
        return bool(kwargs.get('known_domain_info', None) or self.known_domain_info)

    def isUpdateRequired(self, *args, **kwargs):
        """
        Condition method.
        """
        return zdomains.check_nameservers_changed( 
            domain_object=(kwargs.get('target_domain', None) or self.target_domain),
            domain_info_response=(kwargs.get('known_domain_info', None) or self.known_domain_info),
        )

    def isDomainUpdateNow(self, *args, **kwargs):
        """
        Condition method.
        """
        return self.update_domain

    def doInit(self, *args, **kwargs):
        """
        Action method.
        """
        self.target_domain = kwargs['target_domain']
        self.known_domain_info = kwargs.get('known_domain_info', None)

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
            self.known_domain_info = response
            self.event('response', response)

    def doPrepareHosts(self, *args, **kwargs):
        """
        Action method.
        """
        self.hosts_to_be_added = []
        self.hosts_to_be_removed = []
        self.hosts_to_be_added, self.hosts_to_be_removed = zdomains.compare_nameservers(
            domain_object=self.target_domain,
            domain_info_response=self.known_domain_info,
        )

    def doEppHostCheckMany(self, *args, **kwargs):
        """
        Action method.
        """
        if not self.hosts_to_be_added:
            self.event('no-hosts-to-be-added')
            return
        try:
            check_host = rpc_client.cmd_host_check(self.hosts_to_be_added)
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppHostCheckMany: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', check_host)

    def doEppHostCreateMany(self, *args, **kwargs):
        """
        Action method.
        """
        check_host_results = args[0]['epp']['response']['resData']['chkData']['cd']
        if isinstance(check_host_results, dict):
            check_host_results = [check_host_results, ]
        for host_avail in check_host_results:
            if host_avail['name']['@avail'] == '1':
                try:
                    create_host = rpc_client.cmd_host_create(host_avail['name']['#text'])
                except rpc_error.EPPError as exc:
                    self.log(self.debug_level, 'Exception in doEppHostCreateMany: %s' % exc)
                    self.event('error', exc)
                    return
                # TODO: check that scenario later : probably hostname format is not valid or some other issue on back-end
                # can be that we just mark that hostname as invalid or "not-in-sync"... 
                # if create_host['epp']['response']['result']['@code'] == '2303':
                #     return False
                if create_host['epp']['response']['result']['@code'] != '1000':
                    logger.error('bad result code from host_create: %s', create_host['epp']['response']['result']['@code'])
                    self.event('error')
                    return
                self.outputs.append(create_host)
        self.event('all-hosts-created')

    def doEppDomainUpdate(self, *args, **kwargs):
        """
        Action method.
        """
        try:
            domain_update = rpc_client.cmd_domain_update(
                self.target_domain.name,
                add_nameservers_list=self.hosts_to_be_added,
                remove_nameservers_list=self.hosts_to_be_removed,
            )
        except rpc_error.EPPError as exc:
            self.log(self.debug_level, 'Exception in doEppDomainUpdate: %s' % exc)
            self.event('error', exc)
        else:
            self.event('response', domain_update)

    def doReportDone(self, *args, **kwargs):
        """
        Action method.
        """
        if args:
            self.outputs.append(args[0])

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
        self.known_domain_info = None
        self.update_domain = None
        self.hosts_to_be_added = None
        self.hosts_to_be_removed = None
        self.destroy()


