#!/usr/bin/python

import logging
import json
import time
import datetime

from lib import xml2json

from django.utils import timezone
from django.conf import settings

from base.email import send_email

from epp import rpc_client
from epp import rpc_error

from zen import zmaster
from zen import zdomains

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class XML2JsonOptions(object):
    pretty = True

#------------------------------------------------------------------------------

def do_domain_transfer_in(domain):
    logger.info('domain %s transferred to Zenaida', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=True,
            create_new_owner_allowed=True,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain %s from back-end' % domain)
        return False
    if not outputs:
        logger.critical('synchronize domain %s failed with empty result' % domain)
        return False
    if not outputs[-1] or isinstance(outputs[-1], Exception):
        logger.critical('synchronize domain %s failed with result: %r', domain, outputs[-1])
        return False
    logger.info('outputs: %r', outputs)
    domain_object = zdomains.domain_find(domain_name=domain)
    if not domain_object:
        logger.critical('synchronize domain %s failed, no domain object found' % domain)
        return False
    return True


def do_domain_transfer_away(domain, from_client=None, to_client=None, notify=False):
    logger.info('domain %s transferred away', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=False,
            change_owner_allowed=True,
            soft_delete=True,
            domain_transferred_away=True,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True


def do_domain_deleted(domain, soft_delete=True, notify=False):
    logger.info('domain %s deleted', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=False,
            change_owner_allowed=True,
            soft_delete=soft_delete,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True


def do_domain_status_changed(domain, notify=False):
    logger.info('domain %s status changed', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=False,
            change_owner_allowed=False,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True


def do_domain_restored(domain, notify=False):
    logger.info('domain %s was restored', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=True,
            create_new_owner_allowed=True,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True


def do_domain_renewal(domain, ex_date=None, notify=False):
    logger.info('domain %s renewal', domain)
    site_name = settings.SITE_BASE_URL.replace("https://","")
    if False:
        for admin_email in settings.ZENAIDA_ADMIN_NOTIFY_EMAILS:
            try:
                send_email(
                    subject=f'{site_name}: domain {domain} renewal',
                    text_content=f'Domain {domain} registered by {site_name} was automatically renewed on the back-end system',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_email=admin_email,
                )
            except:
                logger.exception('alert EMAIL sending failed')
    current_expiry_date = None
    existing_domain_object = zdomains.domain_find(domain_name=domain)
    if existing_domain_object:
        current_expiry_date = existing_domain_object.expiry_date
    synchronize_failed = False
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=True,
            create_new_owner_allowed=True,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        synchronize_failed = True
    existing_domain_object = zdomains.domain_find(domain_name=domain)
    next_expiry_date = existing_domain_object.expiry_date if existing_domain_object else None
    if not current_expiry_date:
        logger.warn('new expiry date was not identified for %r, populate date from today', domain)
        current_expiry_date = timezone.now()
    if next_expiry_date and current_expiry_date:
        renew_years = int(round((next_expiry_date - current_expiry_date).days / 365.0))
        if not renew_years or renew_years < 0:
            logger.warn('renew duration was not correctly identified for %r, assuming renew durating of 2 years', domain)
        current_expiry_date = next_expiry_date - datetime.timedelta(days=365*2)
    from billing import orders as billing_orders
    notification = zmaster.create_back_end_renew_notification(
        domain_name=domain,
        next_expiry_date=next_expiry_date,
        previous_expiry_date=current_expiry_date,
        restore_order=billing_orders.find_latest_processed_domain_restore_order(domain_name=domain),
    )
    if synchronize_failed or not outputs:
        logger.critical('synchronize domain %s failed with empty result' % domain)
        notification.status = 'failed'
        notification.details = {'errors': ['synchronize domain %s failed with empty result' % domain, ]}
        notification.save()
        return False
    if not outputs[-1] or isinstance(outputs[-1], Exception):
        logger.critical('synchronize domain %s failed with result: %r', domain, outputs[-1])
        notification.status = 'failed'
        notification.details = {'errors': ['synchronize domain %s failed with result: %r' % (domain, outputs[-1]), ]}
        notification.save()
        return False
    logger.info('outputs: %r', outputs)
    domain_object = zdomains.domain_find(domain_name=domain)
    if not domain_object:
        logger.critical('synchronize domain %s failed, no domain object found' % domain)
        notification.status = 'failed'
        notification.details = {'errors': ['synchronize domain %s failed, no domain object found' % domain, ]}
        notification.save()
        return False
    logger.info('domain object: %r', domain_object)
    try:
        zmaster.process_back_end_renew_notification(notification, domain_object)
    except Exception as exc:
        logger.exception('failed processing of the notification %r for %r: %r' % (notification, domain_object, exc, ))
        notification.status = 'failed'
        notification.details = {'errors': ['failed processing of the notification %r for %r: %r' % (notification, domain_object, exc, ), ]}
        notification.save()
        return False
    logger.info('domain renew notification processed successfully: %r', notification)
    return True


def do_domain_expiry_date_updated(domain):
    logger.info('domain %s expiry date updated', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=False,
            change_owner_allowed=False,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True


def do_domain_create_date_updated(domain):
    logger.info('domain %s create date updated', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=False,
            change_owner_allowed=False,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True


def do_domain_nameservers_changed(domain):
    logger.info('domain %s nameservers changed', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=False,
            change_owner_allowed=False,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True


def do_domain_contacts_changed(domain):
    logger.info('domain %s contacts changed', domain)
    # step 1: read info from back-end and make changes in local DB
    try:
        outputs1 = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=True,
            create_new_owner_allowed=True,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs1: %r', outputs1)
    # step 2: write changes to back-end
    try:
        outputs2 = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=True,
            rewrite_contacts=True,
            change_owner_allowed=False,
        )
    except rpc_error.EPPError:
        logger.exception('failed to re-write domain info on back-end: %s' % domain)
        return False
    logger.info('outputs2: %r', outputs2)
    # step 3: read again latest info from back-end and make sure all contacts are refreshed
    try:
        outputs3 = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=False,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain contacts from back-end: %s' % domain)
        return False
    logger.info('outputs3: %r', outputs3)
    return True


def do_domain_change_unknown(domain):
    logger.info('domain %s change is unknown, doing hard-synchronize', domain)
    try:
        outputs = zmaster.domain_synchronize_from_backend(
            domain_name=domain,
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=True,
            create_new_owner_allowed=True,
        )
    except rpc_error.EPPError:
        logger.exception('failed to synchronize domain from back-end: %s' % domain)
        return False
    logger.info('outputs: %r', outputs)
    return True

#------------------------------------------------------------------------------

def on_queue_response(resData):
    if 'trnData' in resData:
        try:
            domain = str(resData['trnData']['name'])
            trStatus = str(resData['trnData']['trStatus'])
            from_client = resData['trnData']['acID']
            to_client = resData['trnData']['reID']
        except:
            logger.exception('can not process queue response: %s' % resData)
            return False

        if trStatus.lower() not in ['serverapproved', 'clientapproved', ]:
            logger.info('domain %s transfer status is: %s' % (domain, trStatus, ))
            return True

        if to_client.lower() == settings.ZENAIDA_REGISTRAR_ID.lower():
            return do_domain_transfer_in(domain)

        return do_domain_transfer_away(domain, from_client=from_client, to_client=to_client)

    if 'renData' in resData:
        try:
            domain = str(resData['renData']['name'])
        except:
            logger.exception('can not process queue response: %s' % resData)
            return False
        try:
            exDate = str(resData['renData']['exDate'])
        except:
            logger.exception('unexpected queue response structure: %s' % resData)
            exDate = None

        return do_domain_renewal(domain, ex_date=exDate)

    logger.error('UNKNOWN response: %s' % resData)
    return False


def on_queue_message(msgQ):
    try:
        msg_element = msgQ['msg']
    except:
        logger.exception('can not process queue message: %s' % msgQ)
        return False

    if isinstance(msg_element, dict):
        msg_text = msg_element.get('#text')
    else:
        msg_text = str(msg_element)

    if not msg_text:
        logger.error('unexpected payload received: %r' % msgQ)
        return True

    if msg_text.lower().count('alert') and msg_text.lower().count('balance'):
        site_name = settings.SITE_BASE_URL.replace("https://","")
        for admin_email in settings.ZENAIDA_ADMIN_NOTIFY_EMAILS:
            try:
                send_email(
                    subject=f'{site_name}: Admin alert',
                    text_content=msg_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_email=admin_email,
                )
            except:
                logger.exception('alert EMAIL sending failed')
        logger.warn(msg_text)
        return True

    if msg_text.lower().count('delete requested: '):
        domain = msg_text.lower().replace('delete requested: ', '')
        logger.info('received removal request for domain %r', domain)
        return True

    if msg_text.lower().count('restore requested: '):
        domain = msg_text.lower().replace('restore requested: ', '')
        logger.info('received restore request for domain %r', domain)
        return True

    if msg_text.lower().count('restore completed: '):
        domain = msg_text.lower().replace('restore completed: ', '')
        logger.info('received restore completed notification for domain %r', domain)
        return do_domain_restored(domain)

    if msg_text.lower().count('delete completed: '):
        domain = msg_text.lower().replace('delete completed: ', '')
        logger.info('received delete completed notification for domain %r', domain)
        return do_domain_deleted(domain)

    if msg_text.lower().count('pending delete: '):
        domain = msg_text.lower().replace('pending delete: ', '')
        logger.info('received pending delete notification for domain %r', domain)
        return do_domain_deleted(domain)

    try:
        json_input = json.loads(xml2json.xml2json(msg_text, XML2JsonOptions(), strip_ns=1, strip=1))
    except:
        logger.exception('can not process queue message: %s' % msgQ)
        return False

    if 'offlineUpdate' in json_input:
        try:
            domain = str(json_input['offlineUpdate']['domain']['name'])
            change = str(json_input['offlineUpdate']['domain']['change'])
            details = str(json_input['offlineUpdate']['domain']['details'])
        except:
            logger.exception('can not process queue json message: %s' % json_input)
            return False

        if change == 'TRANSFER':
            if details.lower() == 'domain transferred away':
                return do_domain_transfer_away(domain)

            if details.lower() == 'domain transferred':
                return do_domain_transfer_in(domain)

            if details.lower() == 'transfer rejected through ui':
                return False

        if change == 'DELETION':
            if details.lower() == 'domain deleted':
                return do_domain_deleted(domain)
            if details.lower() == 'domain pending delete' or details.lower() == 'domain pending deletion':
                return do_domain_status_changed(domain)

        if change == 'RENEWAL':
            return do_domain_renewal(domain)

        if change == 'RESTORED':
            if details.lower() in ['domain restored', 'domain restored via ui', ]:
                return do_domain_status_changed(domain)
            # TODO: domain to be sync, check other scenarios ?

        if change == 'STATE_CHANGE':
            if details.lower() == 'domain status updated':
                return do_domain_status_changed(domain)
            if details.lower() == 'domain activated':
                return do_domain_status_changed(domain)
            # TODO: domain to be sync, check other scenarios ?

        if change == 'EXCLUSION':
            if details.lower() == 'domain excluded':
                return do_domain_status_changed(domain)
            # TODO: domain to be sync, check other scenarios ?

        if change == 'SUSPENSION':
            if details.lower() == 'domain suspended':
                return do_domain_status_changed(domain)
            # TODO: domain to be sync, check other scenarios ?

        if change == 'DETAILS_CHANGED':
            if details.lower() == 'domain expiry date updated':
                return do_domain_expiry_date_updated(domain)
            if details.lower() == 'domain create date modified':
                return do_domain_create_date_updated(domain)
            # TODO: domain to be sync, check other scenarios ?

        if change == 'CONTACTS_CHANGED':
            return do_domain_contacts_changed(domain)

        if change == 'NAMESERVERS_CHANGED':
            return do_domain_nameservers_changed(domain)

        if change == 'STATE_CHANGE':
            if details.lower() == 'domain deleted':
                return do_domain_deleted(domain)
            if details.lower().count('addperiod_grace'):
                logger.debug('SKIP message: %r', json_input)
                return True
            if details.lower().count('redemption_period'):
                logger.debug('SKIP message: %r', json_input)
                return True

        if change == 'UNKNOWN':
            if details.lower().count('domain epp statuses updated'):
                return do_domain_status_changed(domain)
            # TODO: found that when you change domain auth code directly on backend epp messages coming to Zenaida like that:
            # {'offlineUpdate': {'domain': {'name': 'lala.ai', 'change': 'UNKNOWN', 'details': None}}}
            # need to ask guys from COCCA about that...
            if not details or details.lower() == 'none':
                # for now we can try to do a simple domain sync to at least try to solve the most issues
                return do_domain_change_unknown(domain)

    logger.error('UNKNOWN poll message: %s' % json_input)
    return False


def handle_event(req):
    try:
        resp = req['epp']['response']
    except:
        logger.exception('can not read poll_req response: %s' % req)
        return False

    try:
        if 'resData' in resp:
            return on_queue_response(resp['resData'])
    except:
        logger.exception('can not process poll_req response data: %s' % resp)
        return False

    try:
        if 'msgQ' in resp:
            return on_queue_message(resp['msgQ'])
    except:
        logger.exception('can not process poll_req message: %s' % resp)
        return False

    return False

#------------------------------------------------------------------------------

def main():
    logger.info('polling loop started at %r', time.asctime())
    while True:
        result = False
        while True:
            try:
                req = rpc_client.cmd_poll_req()
                resp_code = str(req['epp']['response']['result']['@code'])
            except:
                logger.exception('ERROR in cmd_poll_req()')
                break

            if resp_code == '1300':
                # No new messages
                # logger.debug('.')
                break

            if resp_code != '1301':
                logger.error('wrong response from EPP: %s', req)
                break

            try:
                msg_id = req['epp']['response']['msgQ']['@id']
                logger.info('msg_id: %r', msg_id)
                rpc_client.cmd_poll_ack(msg_id)
            except:
                logger.exception('ERROR in cmd_poll_ack()')
                break

            try:
                result = handle_event(req)
            except:
                logger.exception('ERROR in handle_event()')
                break

            if result:
                logger.debug('OK!')
                break

            logger.debug('NEXT?')

        if not result:
            time.sleep(settings.ZENAIDA_EPP_POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
