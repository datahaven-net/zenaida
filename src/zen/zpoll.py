#!/usr/bin/python

import logging
import time
import json

from lib import xml2json

from zen import zclient

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class XML2JsonOptions(object):
    pretty = True

#------------------------------------------------------------------------------

def do_domain_transfer_to_us(domain):
    # TODO: implement when required
    logger.info('domain %s transferred to Zenaida', domain)
    return True


def do_domain_transfer_away(domain, from_client=None, to_client=None, notify=False):
    logger.info('domain %s transferred away', domain)
    # TODO: to be continue
    return False


def do_domain_deleted(domain, notify=False):
    logger.info('domain %s deleted', domain)
    # TODO: to be continue
    return False


def do_domain_status_changed(domain, notify=False):
    logger.info('domain %s status changed', domain)
    # TODO: to be continue
    return False


def do_domain_expiry_date_updated(domain):
    logger.info('domain %s expiry date updated', domain)
    # from zen import zmaster
    # zmaster.domain_synchronize_from_backend(domain)
    # TODO: to be continue
    return False


def do_domain_nameservers_changed(domain):
    logger.info('domain %s nameservers changed', domain)
    # TODO: to be continue
    return False


def do_domain_contacts_changed(domain):
    logger.info('domain %s contacts changed', domain)
    # TODO: to be continue
    return False

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

        if trStatus.lower() != 'serverapproved':
            logger.info('domain %s transfer status is: %s' % (domain, trStatus, ))
            return True

        return do_domain_transfer_away(domain, from_client=from_client, to_client=to_client)

    logger.error('UNKNOWN response: %s' % resData)
    return False


def on_queue_message(msgQ):
    try:
        json_input = json.loads(xml2json.xml2json(msgQ['msg']['#text'], XML2JsonOptions(), strip_ns=1, strip=1))
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
                return do_domain_transfer_to_us(domain)

        if change == 'DELETION':
            if details.lower() == 'domain deleted':
                return do_domain_deleted(domain)
            if details.lower() == 'domain pending delete' or details.lower() == 'domain pending deletion':
                return do_domain_status_changed(domain)

        if change == 'RESTORED':
            if details.lower() == 'domain restored':
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
            # TODO: domain to be sync, check other scenarios ?

        if change == 'CONTACTS_CHANGED':
            return do_domain_contacts_changed(domain)

        if change == 'NAMESERVERS_CHANGED':
            return do_domain_nameservers_changed(domain)

        if change == 'UNKNOWN':
            if details.lower().count('domain epp statuses updated'):
                return do_domain_status_changed(domain)
            if details.lower() == 'none':
                return do_domain_transfer_away(domain)

    logger.error('UNKNOWN message: %s' % json_input)
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
                req = zclient.cmd_poll_req()
                resp_code = req['epp']['response']['result']['@code']
            except:
                logger.exception('ERROR in cmd_poll_req()')
                break

            if resp_code == '1300':
                # No new messages
                logger.debug('.')
                break

            if resp_code != '1301':
                logger.error('wrong response from EPP: %s', resp_code)
                break

            try:
                msg_id = req['epp']['response']['msgQ']['@id']
                zclient.cmd_poll_ack(msg_id)
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
            time.sleep(30)


if __name__ == '__main__':
    main()
