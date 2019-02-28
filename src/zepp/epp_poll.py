#!/usr/bin/python

import logging
import os
import sys
import time
import tempfile
import json
import string

# from email.Utils import formatdate, parsedate

from zepp import xml2json
from zepp import zclient
from zepp import zmaster

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
    return False
#     dpath = scanForDomain(domain)
#     if dpath == 'error':
#         print '\n%s' % time.asctime()
#         print '\ncan not find domain form "%s"' % domain
#         return False
#     if dpath == 'free':
#         print '\n%s' % time.asctime()
#         print '\ndomain "%s" is free, can not be transferred away' % domain
#         return False
#     try:
#         db = loadDB(named_path())
#         dform = {}
#         fin = open(dpath, 'r')
#         readform(dform, fin)
#         fin.close()
#         write2logDir(dform)
#         if os.path.isfile(dpath):
#             fd, _ = tempfile.mkstemp(
#                 prefix='{}.'.format(domain),
#                 dir=deleted_domains_path()
#             )
#             os.write(fd, open(dpath, 'r').read())
#             os.close(fd)
#         os.remove(dpath)
#         if domain in db:
#             del db[domain]
#         if dform['4l.'].strip() != '':
#             if notify and not TESTING():
#                 sendDomainTransferredNotification(dform['4l.'].strip(), domain)
#             removeUserDomain(dform['4l.'].strip(), domain)
#         if dform['5l.'].strip() != '':
#             if notify and not TESTING():
#                 sendDomainTransferredNotification(dform['5l.'].strip(), domain)
#             removeUserDomain(dform['5l.'].strip(), domain)
#         if dform['6l.'].strip() != '':
#             if notify and not TESTING():
#                 sendDomainTransferredNotification(dform['6l.'].strip(), domain)
#             removeUserDomain(dform['6l.'].strip(), domain)
#         epp_master.delete_domain_epp_info(domain)
#         remove_domains_from_index([domain, ])
#         writeDB(db, named_path())
#     except Exception as exc:
#         epp_client.log_epp_errors(epp_errors=['failed processing domain "%s" transfer to another registrar' % domain, ])
#         print '\n%s' % time.asctime()
#         print '\nfailed processing domain "%s" transfer to another registrar: %s' % (domain, str(exc))
#         return False
#     if to_client:
#         print '\n%s' % time.asctime()
#         print '\ndomain', domain, 'transferred to', to_client
#     else:
#         print '\n%s' % time.asctime()
#         print '\ndomain', domain, 'transferred away'
#     return True


def do_domain_deleted(domain, notify=False):
    logger.info('domain %s deleted', domain)
    return False
#     dpath = scanForDomain(domain)
#     if dpath == 'error':
#         print '\n%s' % time.asctime()
#         print '\ncan not find domain form "%s"' % domain
#         return False
#     if dpath == 'free':
#         print '\n%s' % time.asctime()
#         print '\ndomain "%s" is free, can not be deleted' % domain
#         return False
#     try:
#         db = loadDB(named_path())
#         dform = {}
#         fin = open(dpath, 'r')
#         readform(dform, fin)
#         fin.close()
#         write2logDir(dform)
#         if os.path.isfile(dpath):
#             fd, _ = tempfile.mkstemp(
#                 prefix='{}.'.format(domain),
#                 dir=deleted_domains_path()
#             )
#             os.write(fd, open(dpath, 'r').read())
#             os.close(fd)
#         os.remove(dpath)
#         if domain in db:
#             del db[domain]
#         if dform['4l.'].strip() != '':
#             if notify and not TESTING():
#                 sendDomainDeleteNotification(dform['4l.'].strip(), domain)
#             removeUserDomain(dform['4l.'].strip(), domain)
#         if dform['5l.'].strip() != '':
#             if notify and not TESTING():
#                 sendDomainDeleteNotification(dform['5l.'].strip(), domain)
#             removeUserDomain(dform['5l.'].strip(), domain)
#         if dform['6l.'].strip() != '':
#             if notify and not TESTING():
#                 sendDomainDeleteNotification(dform['6l.'].strip(), domain)
#             removeUserDomain(dform['6l.'].strip(), domain)
#         epp_master.delete_domain_epp_info(domain)
#         remove_domains_from_index([domain, ])
#         writeDB(db, named_path())
#     except Exception as exc:
#         epp_client.log_epp_errors(epp_errors=['failed processing domain "%s" deletion' % domain, ])
#         print '\n%s' % time.asctime()
#         print '\nfailed processing domain "%s" deletion: %s' % (domain, str(exc))
#         return False
#     print '\n%s' % time.asctime()
#     print '\ndomain', domain, 'deleted'
#     return True


def do_domain_status_changed(domain, notify=False):
    logger.info('domain %s status changed', domain)
    return False
#     try:
#         old, new = epp_master.do_domain_update_statuses(domain)
#     except:
#         epp_client.log_epp_errors()
#         print '\n%s' % time.asctime()
#         print '\nfailed processing domain "%s" status modifications' % domain
#         return False
#     old_statuses = filter(lambda k: old[k], old)
#     new_statuses = filter(lambda k: new[k], new)
#     if ('pendingDelete' in old_statuses) and ('ok' in new_statuses):
#         # this will only be triggered when user asked to restore domain from pending delete state
#         dpath = scanForDomain(domain)
#         if dpath != 'free' and dpath != 'error':
#             db_changes = False
#             dform = {}
#             try:
#                 fin = open(dpath, 'r')
#                 readform(dform, fin)
#                 fin.close()
#             except:
#                 epp_client.log_epp_errors()
#                 print '\n%s' % time.asctime()
#                 print '\nfailed reading domain "%s" form' % domain
#                 return False
#             epp_info = epp_master.read_domain_epp_info(domain) or {}
#             login = epp_info.get('restore_request', None)
#             if not login:
#                 print '\n%s' % time.asctime()
#                 print '\nunknown request to restore domain "%s", status not in sync' % domain
#                 return False
#             uinfo = {}
#             if not read_info(login, uinfo):
#                 print '\n%s' % time.asctime()
#                 print '\nfailed reading user %s info' % login
#                 return False
#             try:
#                 cur_balance = int(float(uinfo['balance']))
#             except:
#                 print '\n%s' % time.asctime()
#                 print '\nfailed reading user %s balance' % login
#                 return False
#             results, errors = epp_master.domains_synchronize([domain, ], renew=True, renew_years=2, fix_errors=True)
#             if errors:
#                 print '\n%s' % time.asctime()
#                 print '\ndomain %s status changed, but errors happened: %s' % (domain, errors, )
#                 return False
#             cur_balance -= 200
#             uinfo['balance'] = str(cur_balance)
#             save_info(login, uinfo)
#             invoice = addBalancePayment(
#                 domain+';',
#                 login,
#                 success=('successful>>>' + formatdate(time.time(), True) + ' from balance ' + domain),
#             )
#             addUserDomain(login, domain, expire=dform['1b.'])
#             print '\n%s' % time.asctime()
#             print '\ndomain "%s" restored, user %s spent 200$' % (domain, login, )
#     if notify:
#         dpath = scanForDomain(domain)
#         try:
#             dform = {}
#             fin = open(dpath, 'r')
#             readform(dform, fin)
#             fin.close()
#         except:
#             epp_client.log_epp_errors()
#         else:
#             if dform['4l.'].strip() != '':
#                 sendDomainStatusChangedNotification(dform['4l.'].strip(), domain, new_statuses)
#             if dform['5l.'].strip() != '':
#                 sendDomainStatusChangedNotification(dform['5l.'].strip(), domain, new_statuses)
#             if dform['6l.'].strip() != '':
#                 sendDomainStatusChangedNotification(dform['6l.'].strip(), domain, new_statuses)
#     print '\n%s' % time.asctime()
#     print '\ndomain %s status changed,   old=%s   new=%s' % (domain, old_statuses, new_statuses, )
#     return True


def do_domain_expiry_date_updated(domain):
    logger.info('domain %s expiry date updated', domain)
    return False
#     results, errors = epp_master.domains_synchronize([domain, ], renew=False, fix_errors=True)
#     if errors:
#         print '\n%s' % time.asctime()
#         print '\ndomain %s expiry date updated, but error happened: %s' % (domain, errors, )
#         return False
# #     if not do_domain_status_changed(domain):
# #         print '\n%s' % time.asctime()
# #         print '\ndomain %s expiry date updated, but error happened during EPP status sync' % domain
# #         return False
#     print '\n%s' % time.asctime()
#     print '\ndomain %s expiry date updated' % domain
#     return True

def do_domain_nameservers_changed(domain):
    logger.info('domain %s nameservers changed', domain)
    return False

#------------------------------------------------------------------------------

def on_queue_response(resData):
    if 'trnData' in resData:
        try:
            domain = str(resData['trnData']['name'])
            trStatus = str(resData['trnData']['trStatus'])
            from_client = resData['trnData']['acID']
            to_client = resData['trnData']['reID']
        except Exception as exc:
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
    except Exception as exc:
        logger.exception('can not process queue message: %s' % msgQ)
        return False

    if 'offlineUpdate' in json_input:
        try:
            domain = str(json_input['offlineUpdate']['domain']['name'])
            change = str(json_input['offlineUpdate']['domain']['change'])
            details = str(json_input['offlineUpdate']['domain']['details'])
        except Exception as exc:
            logger.exception('can not process queue json message: %s' % json_input)
            return False

        if change == 'CONTACTS_CHANGED':
            # TODO: take action to keep DB domain in sync
            logger.warn('CONTACTS_CHANGED for %s' % domain)
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
            # TODO: DB domain to be in sync - need to check other scenarios during restore

        if change == 'STATE_CHANGE':
            if details.lower() == 'domain status updated':
                return do_domain_status_changed(domain)
            if details.lower() == 'domain activated':
                return do_domain_status_changed(domain)

        if change == 'EXCLUSION':
            if details.lower() == 'domain excluded':
                return do_domain_status_changed(domain)
            # TODO: check other scenarios ?

        if change == 'SUSPENSION':
            if details.lower() == 'domain suspended':
                return do_domain_status_changed(domain)
            # TODO: check other scenarios ?

        if change == 'DETAILS_CHANGED':
            if details.lower() == 'domain expiry date updated':
                return do_domain_expiry_date_updated(domain)
            # TODO: domain to be sync, check other scenarios ?
        
        if change == 'NAMESERVERS_CHANGED':
            return do_domain_nameservers_changed(domain)
            # TODO: take action to keep DB domain in sync
            # logger.warn('NAMESERVERS_CHANGED for %s' % domain)
            # return False

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
            except Exception as exc:
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
            except Exception as exc:
                logger.exception('ERROR in cmd_poll_ack()')
                break

            try:
                result = handle_event(req)
            except Exception as exc:
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
