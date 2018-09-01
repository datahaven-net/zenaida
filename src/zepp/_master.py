import os
import sys
import time
import datetime
import json
import tempfile

from email.utils import parsedate, formatdate

#------------------------------------------------------------------------------

from zepp import client as epp_client
from zepp.client import EPPBadResponse, EPPCommandFailed, EPPCommandInvalid, EPPResponseFailed

#------------------------------------------------------------------------------

epp_domains_dir = ''
deleted_domains_path = ''

#------------------------------------------------------------------------------

def read_domain_epp_info(domain):
    epp_domain_path = os.path.join(epp_domains_dir, domain)
    if not os.path.isfile(epp_domain_path):
        return None
    fin = open(epp_domain_path, 'rb')
    src = fin.read()
    fin.close()
    try:
        epp_info = json.loads(src)
    except:
        epp_info = None
    return epp_info


def write_domain_epp_info(domain, info, do_backup=True):
    epp_domain_path = os.path.join(epp_domains_dir, domain)
    if do_backup:
        domains.writeEPPInfo2logDir(info, domain=domain)
        if os.path.isfile(epp_domain_path):
            fd, _ = tempfile.mkstemp(
                prefix='{}.epp.'.format(domain),
                dir=deleted_domains_path
            )
            os.write(fd, open(epp_domain_path, 'r').read())
            os.close(fd)
    fout = open(epp_domain_path, 'wb')
    fout.write(json.dumps(info, indent=2, sort_keys=True))
    fout.close()


def delete_domain_epp_info(domain, do_backup=True):
    epp_domain_path = os.path.join(epp_domains_dir, domain)
    if not os.path.isfile(epp_domain_path):
        return False
    if do_backup:
        domains.writeEPPInfo2logDir({}, domain=domain)
        if os.path.isfile(epp_domain_path):
            fd, _ = tempfile.mkstemp(
                prefix='{}.epp.'.format(domain),
                dir=deleted_domains_path
            )
            os.write(fd, open(epp_domain_path, 'r').read())
            os.close(fd)
    try:
        os.remove(epp_domain_path)
    except:
        epp_client.log_epp_errors()
        return False
    return True

#------------------------------------------------------------------------------

def do_domain_recover_contacts(domain, do_backup=True):
    epp_domain_info = read_domain_epp_info(domain) or {}
    if 'name' not in epp_domain_info:
        epp_domain_info['name'] = domain
    epp_domain_info.pop('registrant', None)
    epp_domain_info.pop('contact_admin', None)
    epp_domain_info.pop('contact_billing', None)
    epp_domain_info.pop('contact_tech', None)
    write_domain_epp_info(domain, epp_domain_info, do_backup=do_backup)
    return contacts_check_create_update(domain, create_registrant=True, update_domain=True)

#------------------------------------------------------------------------------

def do_domain_create(domain, dform=None, epp_info=None, do_backup=True):
    """
    """
    domain_path = domains.domainPath(domain)
    if not dform:
        dform = {}
        fin = open(domains.domainPath(domain), 'r')
        domains.readform(dform, fin)
        fin.close()
    if not epp_info:
        epp_info = read_domain_epp_info(domain) or {}
    write_domain_epp_info(domain, epp_info)
    domains.write2logDir(dform)
    if do_backup:
    #--- DO BACKUP DOMAIN FORM
        if os.path.isfile(domain_path):
            fd, _ = tempfile.mkstemp(
                prefix='{}.'.format(domain),
                dir=deleted_domains_path
            )
            os.write(fd, open(domain_path, 'r').read())
            os.close(fd)
    #--- WRITE DOMAIN FILES
    fout = open(domain_path + '.tmp', 'w')
    domains.printform(dform, fout)
    os.fsync(fout)
    fout.close()
    os.rename(domain_path + '.tmp', domain_path)
    if dform['4l.'].strip() != '':
        users.addUserDomain(dform['4l.'].strip(), domain)
    if dform['5l.'].strip() != '':
        users.addUserDomain(dform['5l.'].strip(), domain)
    if dform['6l.'].strip() != '':
        users.addUserDomain(dform['6l.'].strip(), domain)
    return True

#------------------------------------------------------------------------------

def do_domain_delete(domain, email_notify=False, reason='transfer', reindex=False, dobackup=False, updatedb=False):
    dpath = domains.scanForDomain(domain)
    if dpath == 'error':
        return 'error'
    if dpath == 'free':
        return 'free'
    try:
        if updatedb:
            db = aidb.loadDB(named_path())
        else:
            db = {}
        dform = {}
        fin = open(dpath, 'r')
        domains.readform(dform, fin)
        fin.close()
        domains.write2logDir(dform)
        if dobackup and os.path.isfile(dpath):
            fd, _ = tempfile.mkstemp(
                prefix='{}.'.format(domain),
                dir=deleted_domains_path
            )
            os.write(fd, open(dpath, 'r').read())
            os.close(fd)
        os.remove(dpath)
        if updatedb:
            if domain in db:
                del db[domain]
        if dform['4l.'].strip() != '':
            if email_notify:
                if reason == 'transfer':
                    users.sendDomainTransferredNotification(dform['4l.'].strip(), domain)
            users.removeUserDomain(dform['4l.'].strip(), domain)
        if dform['5l.'].strip() != '':
            if email_notify:
                if reason == 'transfer':
                    users.sendDomainTransferredNotification(dform['5l.'].strip(), domain)
            users.removeUserDomain(dform['5l.'].strip(), domain)
        if dform['6l.'].strip() != '':
            if email_notify:
                if reason == 'transfer':
                    users.sendDomainTransferredNotification(dform['6l.'].strip(), domain)
            users.removeUserDomain(dform['6l.'].strip(), domain)
        if reindex:
            users.remove_domains_from_index([domain, ] )
        if updatedb:
            aidb.writeDB(db, named_path())
    except:
        epp_client.log_epp_errors(epp_errors=['failed processing domain "%s" deletion' % domain, ])
        return 'failed'
    return 'OK!'

#------------------------------------------------------------------------------

def do_domain_update(domain, changes, email_notify=False, reindex=False, dobackup=False, updatedb=False):
    dpath = domains.scanForDomain(domain)
    if dpath == 'error':
        return 'error'
    if dpath == 'free':
        return 'free'
    try:
        if updatedb:
            db = aidb.loadDB(named_path())
        else:
            db = {}
        dform = {}
        fin = open(dpath, 'r')
        domains.readform(dform, fin)
        fin.close()
        domains.write2logDir(dform)
        if dobackup and os.path.isfile(dpath):
            fd, _ = tempfile.mkstemp(
                prefix='{}.'.format(domain),
                dir=deleted_domains_path
            )
            os.write(fd, open(dpath, 'r').read())
            os.close(fd)

        modified = False
        for field, value in changes.items():
            if field in dform and dform[field] != value:
                dform[field] = value
                modified = True

        if modified:
            fout = open(dpath + '.tmp', 'w')
            domains.printform(dform, fout)
            fout.flush()
            os.fsync(fout)
            fout.close()
            os.rename(dpath + '.tmp', dpath)

        if reindex:
            users.remove_domains_from_index([domain, ] )

        if updatedb:
            aidb.writeDB(db, named_path())
    except:
        epp_client.log_epp_errors(epp_errors=['failed processing domain "%s" modifications' % domain, ])
        return 'failed'
    return 'OK!'


#------------------------------------------------------------------------------

def domain_exist(domain):
    #--- CHECK DOMAIN
    if not domains.checkDomainName(domain):
        raise EPPCommandInvalid('domain name incorrect')
    check = epp_client.cmd_domain_check([domain, ], )
    if check['epp']['response']['result']['@code'] != '1000':
        raise EPPCommandFailed('EPP domain_check failed with error code: %s' % (
            check['epp']['response']['result']['@code'], ))
    if check['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '1':
        return False
    if not check['epp']['response']['resData']['chkData']['cd']['reason'].startswith('(00)'):
        raise EPPCommandFailed('EPP domain_check failed with reason: %s' % (
            check['epp']['response']['resData']['chkData']['cd']['reason']))
    return True

#------------------------------------------------------------------------------

def domain_info(domain, auth_info=None):
    if auth_info is None:
        epp_domain_info = read_domain_epp_info(domain) or {}
        if 'registrant' in epp_domain_info:
            auth_info = epp_domain_info['registrant']['pw']
    #--- GET DOMAIN INFO
    info = epp_client.cmd_domain_info(domain, auth_info=auth_info, raise_for_result=False)
    if info['epp']['response']['result']['@code'] != '1000':
        return None
    return info['epp']['response']['resData']['infData']

#------------------------------------------------------------------------------

def domains_check_verify(domains_list, check=True, verify=True):
    available_domains = {}
    errors = []
    #--- CHECK DOMAINS
    if check:
        chk = epp_client.cmd_domain_check(domains_list)
        if chk['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP domain_check failed with error code: %s' % (
                chk['epp']['response']['result']['@code'], ))
        check_domain_results = chk['epp']['response']['resData']['chkData']['cd']
        if isinstance(check_domain_results, dict):
            check_domain_results = [check_domain_results, ]
        for res in check_domain_results:
            if res['name']['@avail'] == '1':
                available_domains[res['name']['#text']] = None
            else:
                if not res['reason'].startswith('(00)'):
                    raise EPPCommandFailed('EPP domain_check failed with reason: %s' % res['reason'])
                available_domains[res['name']['#text']] = dict()
    else:
        for _domain in domains_list:
            available_domains[_domain] = dict()
    for domain in list(available_domains.keys()):
        if available_domains[domain] is None:
            continue
        epp_domain_info = read_domain_epp_info(domain) or {}
        if not epp_domain_info:
            errors.append('no EPP info records found for domain %s' % domain)
            continue
        available_domains[domain]['local_info'] = epp_domain_info
        auth_info = None
        if 'registrant' in epp_domain_info:
            auth_info = epp_domain_info['registrant']['pw']
        if verify:
    #--- GET DOMAIN INFO
            info = epp_client.cmd_domain_info(domain, auth_info=auth_info)
            if info['epp']['response']['result']['@code'] != '1000':
                raise EPPCommandFailed('EPP domain_info failed with error code: %s' % (
                    info['epp']['response']['result']['@code'], ))
            available_domains[domain]['remote_info'] = info['epp']['response']['resData']['infData']
            if 'registrant' in epp_domain_info:
                if info['epp']['response']['resData']['infData'].get('registrant', None) != epp_domain_info['registrant']['id']:
                    errors.append('domain %s belongs to another registrant' % domain)
                    available_domains[domain] = None
    return (available_domains, errors)

#------------------------------------------------------------------------------

def domain_get_full_info(domain, verify_owner=True, auth_info=None):
    epp_domain_info = read_domain_epp_info(domain) or {}
    if not auth_info:
        if 'registrant' in epp_domain_info:
            auth_info = epp_domain_info['registrant']['pw']
    #--- GET DOMAIN INFO
    info = epp_client.cmd_domain_info(domain, auth_info=auth_info)
    if info['epp']['response']['result']['@code'] != '1000':
        raise EPPCommandFailed('EPP domain_info failed with error code: %s' % (
            info['epp']['response']['result']['@code'], ))
    try:
        req_registrant_id = info['epp']['response']['resData']['infData']['registrant']
    except:
        req_registrant_id = None
    #--- VERIFY OWNER
    if verify_owner and 'registrant' in epp_domain_info:
        if req_registrant_id is None or req_registrant_id != epp_domain_info['registrant']['id']:
            raise EPPCommandInvalid('domain %s belongs to another registrant' % domain)

    def _date_transform(epp_date):
        if not epp_date:
            return ''
        return formatdate(time.mktime(datetime.datetime.strptime(
            epp_date, '%Y-%m-%dT%H:%M:%S.%fZ').timetuple()), True)

    result = {
        'name': info['epp']['response']['resData']['infData']['name'],
        'roid': str(info['epp']['response']['resData']['infData']['roid']),
        'crDate': _date_transform(info['epp']['response']['resData']['infData'].get('crDate', '')),
        'upDate': _date_transform(info['epp']['response']['resData']['infData'].get('upDate', '')),
        'exDate': _date_transform(info['epp']['response']['resData']['infData'].get('exDate', '')),
        'admin': {},
        'tech': {},
        'billing': {},
        'registrant': {},
        'hostnames': [],
    }
    try:
        current_contacts = info['epp']['response']['resData']['infData']['contact']
    except:
        current_contacts = []
    if not isinstance(current_contacts, list):
        current_contacts = [current_contacts, ]
    current_contacts = [{'type': i['@type'], 'id': i['#text']} for i in current_contacts]

    def _extract_postal_info(pi):
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

    for contact in current_contacts:
    #--- GET CONTACT INFO
        cont_info = epp_client.cmd_contact_info(contact['id'])
        if cont_info['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP contact_info failed with error code: %s' % (
                cont_info['epp']['response']['result']['@code'], ))
        d = cont_info['epp']['response']['resData']['infData']
        result[contact['type']] = {
            'id': str(d['id']),
            'email': str(d['email']),
            'voice': str(d.get('voice', '')),
            'fax': str(d.get('fax', '')),
        }
        postal_info_list = d['postalInfo'] if isinstance(d['postalInfo'], list) else [d['postalInfo'], ]
        local_address = False
        for postal_info in postal_info_list:
            if postal_info['@type'] == 'loc':
                local_address = True
                result[contact['type']].update(_extract_postal_info(postal_info))
                break
        if not local_address:
            for postal_info in postal_info_list:
                result[contact['type']].update(_extract_postal_info(postal_info))
    if req_registrant_id is not None:
    #-- GET REGISTRANT INFO
        reg_info = epp_client.cmd_contact_info(req_registrant_id)
        if reg_info['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP contact_info failed with error code: %s' % (
                reg_info['epp']['response']['result']['@code'], ))
        d = reg_info['epp']['response']['resData']['infData']
        result['registrant'] = {
            'id': str(d['id']),
            'email': str(d.get('email', '')),
            'voice': str(d.get('voice', '')),
            'fax': str(d.get('fax', '')),
        }
        postal_info_list = d['postalInfo'] if isinstance(d['postalInfo'], list) else [d['postalInfo'], ]
        local_address = False
        for postal_info in postal_info_list:
            if postal_info['@type'] == 'loc':
                local_address = True
                result['registrant'].update(_extract_postal_info(postal_info))
                break
        if not local_address:
            for postal_info in postal_info_list:
                result['registrant'].update(_extract_postal_info(postal_info))
    try:
        result['hostnames'] = info['epp']['response']['resData']['infData']['ns']['hostObj']
    except:
        result['hostnames'] = []
    if not isinstance(result['hostnames'], list):
        result['hostnames'] = [result['hostnames'], ]
    return result

#------------------------------------------------------------------------------

def contacts_check_create_update(domain, dform={}, create_registrant=True, update_domain=False, local_sync=True):
    epp_domain_info = read_domain_epp_info(domain) or {}
    contacts_ids = {}
    errors = []
    updated = False
    if not epp_domain_info:
        epp_domain_info['name'] = domain
    if not dform:
        dform = {}
        fin = open(domains.domainPath(domain), 'r')
        domains.readform(dform, fin)
        fin.close()
    #--- PREPARE CONTACTS
    domain_contacts = domains.getDomainContactsDict(domain, dform)
    registrant_voice = ''
    for role, contact_role_info in domain_contacts.items():
        contact_epp_id = epp_domain_info.get('contact_' + role, {}).get('id', None)
        c = domains.FixContactInfo(contact_role_info)
        if contact_epp_id:
    #--- UPDATE CONTACT
            contact_voice = (c['voice'] if ('voice' in c) else None)
            if not registrant_voice and contact_voice:
                registrant_voice = contact_voice
            try:
                ret = epp_client.cmd_contact_update(
                    contact_epp_id,
                    email=c['email'],
                    voice=contact_voice,
                    fax=(c['fax'] if ('fax' in c) else None),
                    auth_info=epp_domain_info.get('contact_' + role, {}).get('pw', None),
                    contacts_list=c['contacts'],
                )
            except epp_client.EPPResponseFailed as e:
                errors.append(e.message)
                return errors
            else:
                if ret['epp']['response']['result']['@code'] != '1000':
                    raise EPPCommandFailed('EPP contact_update failed with error code: %s' % (
                        ret['epp']['response']['result']['@code'], ))
                contacts_ids[role] = (contact_epp_id, False, )
        else:
            c['id'] = epp_client.make_epp_id(c['email'])
            auth_info = users.generatePassword()
    #--- CREATE CONTACT
            contact_voice = (c['voice'] if ('voice' in c) else None)
            if not registrant_voice and contact_voice:
                registrant_voice = contact_voice
            if not contact_voice:
                # every contact must have a voice number
                contact_voice = '0'
            try:
                ret = epp_client.cmd_contact_create(
                    c['id'],
                    c['email'],
                    voice=contact_voice,
                    fax=(c['fax'] if ('fax' in c) else None),
                    auth_info=auth_info,
                    contacts_list=c['contacts'],
                )
            except epp_client.EPPResponseFailed as e:
                errors.append(e.message)
                return errors
            else:
                if ret['epp']['response']['result']['@code'] != '1000':
                    if ret['epp']['response']['result']['@code'] != '2302':
                        raise EPPCommandFailed('EPP contact_create failed with error code: %s' % (
                            ret['epp']['response']['result']['@code'], ))
    #--- CREATE CONTACT RETRY
                    c['id'] = epp_client.make_epp_id('a' + c['email'])
                    auth_info = users.generatePassword()
                    try:
                        ret = epp_client.cmd_contact_create(
                            c['id'],
                            c['email'],
                            voice=contact_voice,
                            fax=(c['fax'] if ('fax' in c) else None),
                            auth_info=auth_info,
                            contacts_list=c['contacts'],
                        )
                    except epp_client.EPPResponseFailed as e:
                        raise EPPCommandFailed('EPP contact_create failed: %s' % str(e))
                    else:
                        if ret['epp']['response']['result']['@code'] != '1000':
                            raise EPPCommandFailed('EPP contact_create failed with error code: %s' % (
                                ret['epp']['response']['result']['@code'], ))
                contact_epp_id = ret['epp']['response']['resData']['creData']['id']
                uinfo = {}
                if users.read_info(c['email'], uinfo):
                    uinfo['contact_' + role + '_epp_id'] = contact_epp_id
                    users.save_info(c['email'], uinfo)
                epp_domain_info['contact_' + role] = {
                    'id': contact_epp_id,
                    'pw': auth_info,
                }
                updated = True
                contacts_ids[role] = (contact_epp_id, True, )
    #--- PREPARE REGISTRANT
    registrant_info = domains.getDomainRegistrantInfoDict(domain, dform)
    for role in ['admin', 'tech', 'billing', ]:
        if role in domain_contacts:
            registrant_info['email'] = domain_contacts[role]['email']
            break
    if not registrant_info.get('email', ''):
        registrant_info['email'] = 'datahaven.net@gmail.com'
    registrant_info = domains.FixContactInfo(registrant_info)
    if epp_domain_info.get('registrant'):
    #--- UPDATE REGISTRANT
        try:
            ret = epp_client.cmd_contact_update(
                epp_domain_info['registrant']['id'],
                email=registrant_info['email'],
                auth_info=epp_domain_info['registrant']['pw'],
                contacts_list=registrant_info['contacts'],
            )
        except epp_client.EPPResponseFailed as e:
            errors.append(e.message)
            return errors
        else:
            if ret['epp']['response']['result']['@code'] != '1000':
                raise EPPCommandFailed('EPP contact_update failed with error code: %s' % (
                    ret['epp']['response']['result']['@code'], ))
            contacts_ids['registrant'] = (epp_domain_info.get('registrant', {}).get('id', None), False, )
    else:
        if create_registrant:
            registrant_info['id'] = epp_client.make_epp_id(registrant_info['email'])
            auth_info = users.generatePassword()
    #--- CREATE REGISTRANT
            try:
                ret = epp_client.cmd_contact_create(
                    registrant_info['id'],
                    registrant_info['email'],
                    voice=registrant_voice or '12600000000',
                    auth_info=auth_info,
                    contacts_list=registrant_info['contacts'],
                )
            except epp_client.EPPResponseFailed as e:
                errors.append(e.message)
                return errors
            else:
                if ret['epp']['response']['result']['@code'] != '1000':
                    if ret != '2303':
                        raise EPPCommandFailed('EPP contact_create failed with error code: %s' % (
                            ret['epp']['response']['result']['@code'], ))
    #--- CREATE REGISTRANT RETRY
                    registrant_info['id'] = epp_client.make_epp_id('a' + registrant_info['email'])
                    auth_info = users.generatePassword()
                    try:
                        ret = epp_client.cmd_contact_create(
                            registrant_info['id'],
                            registrant_info['email'],
                            voice=registrant_voice or '12600000000',
                            auth_info=auth_info,
                            contacts_list=registrant_info['contacts'],
                        )
                    except epp_client.EPPResponseFailed as e:
                        raise EPPCommandFailed('EPP contact_create failed: %s' % str(e))
                    else:
                        if ret['epp']['response']['result']['@code'] != '1000':
                            raise EPPCommandFailed('EPP contact_create failed with error code: %s' % (
                                ret['epp']['response']['result']['@code'], ))
                epp_id = ret['epp']['response']['resData']['creData']['id']
                epp_domain_info['registrant'] = {
                    'id': epp_id,
                    'pw': auth_info,
                }
                updated = True
                contacts_ids['registrant'] = (epp_domain_info['registrant']['id'], True, )
        else:
            contacts_ids['registrant'] = (epp_domain_info.get('registrant', {}).get('id', None), False, )
    if not errors and updated and local_sync:
        write_domain_epp_info(domain, epp_domain_info)
    #--- GET DOMAIN INFO
    if not errors and updated and update_domain:
        try:
            info = epp_client.cmd_domain_info(domain, auth_info=epp_domain_info['registrant']['pw'])
        except epp_client.EPPResponseFailed as e:
            errors.append(e.message)
            return errors
        else:
            if info['epp']['response']['result']['@code'] != '1000':
                raise EPPCommandFailed('EPP domain_info failed with error code: %s' % (
                    info['epp']['response']['result']['@code'], ))
            try:
                current_contacts = info['epp']['response']['resData']['infData']['contact']
            except:
                current_contacts = []
            try:
                current_registrant = info['epp']['response']['resData']['infData']['registrant']
            except:
                current_registrant = None
            if not isinstance(current_contacts, list):
                current_contacts = [current_contacts, ]
            current_contacts = [{'type': i['@type'], 'id': i['#text']} for i in current_contacts]
            new_contacts = []
            for role, contact_role_info in domain_contacts.items():
                epp_info = epp_domain_info.get('contact_' + role, {})
                if epp_info:
                    new_contacts.append({'type': role, 'id': epp_info.get('id', None)})
            add_contacts = []
            remove_contacts = []
            for new_cont in new_contacts:
                if new_cont['id'] not in [old_contact['id'] for old_contact in current_contacts]:
                    add_contacts.append(new_cont)
            for old_cont in current_contacts:
                if old_cont['type'] == 'registrant':
                    continue
                if old_cont['id'] not in [new_cont['id'] for new_cont in new_contacts]:
                    remove_contacts.append(old_cont)
            change_registrant = None
            new_auth_info = None
            if current_registrant != epp_domain_info['registrant']['id']:
                change_registrant = epp_domain_info['registrant']['id']
                new_auth_info = epp_domain_info['registrant']['pw']
            if not errors and (remove_contacts or add_contacts):
    #--- UPDATE DOMAIN CONTACTS
                update = epp_client.cmd_domain_update(
                    domain,
                    add_contacts_list=add_contacts,
                    remove_contacts_list=remove_contacts,
                    change_registrant=change_registrant,
                    # auth_info=new_auth_info,
                )
                if update['epp']['response']['result']['@code'] != '1000':
                    raise EPPCommandFailed('EPP domain_update failed with error code: %s' % (
                        update['epp']['response']['result']['@code'], ))
                if local_sync:
                    write_domain_epp_info(domain, epp_domain_info)
    return errors or contacts_ids

#------------------------------------------------------------------------------

def nameservers_check_create_update(domain, new_servers, domain_info=None, update_domain=True):
    if update_domain:
        if domain_info is None:
        #--- GET DOMAIN INFO
            epp_domain_info = read_domain_epp_info(domain) or {}
            auth_info = None
            if 'registrant' in epp_domain_info:
                auth_info = epp_domain_info['registrant']['pw']
            info = epp_client.cmd_domain_info(domain, auth_info=auth_info)
            if info['epp']['response']['result']['@code'] != '1000':
                raise EPPCommandFailed('EPP domain_info failed with error code: %s' % (
                    info['epp']['response']['result']['@code'], ))
        else:
            info = domain_info
        try:
            current_servers = info['epp']['response']['resData']['infData']['ns']['hostObj']
        except:
            current_servers = []
        if not isinstance(current_servers, list):
            current_servers = [current_servers, ]
        to_be_removed = []
        to_be_added = []
        for old_server in current_servers:
            if old_server not in new_servers:
                to_be_removed.append(old_server)
        for new_server in new_servers:
            if new_server not in current_servers:
                to_be_added.append(new_server)
    else:
        to_be_added = new_servers
    if to_be_added:
    #--- CHECK HOST
        check_host = epp_client.cmd_host_check(to_be_added)
        if check_host['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP host_check failed with error code: %s' % (
                check_host['epp']['response']['result']['@code'], ))
        check_host_results = check_host['epp']['response']['resData']['chkData']['cd']
        if isinstance(check_host_results, dict):
            check_host_results = [check_host_results, ]
        for host_avail in check_host_results:
            if host_avail['name']['@avail'] == '1':
    #--- CREATE HOST
                create_host = epp_client.cmd_host_create(host_avail['name']['#text'])
                if create_host['epp']['response']['result']['@code'] == '2303':
                    return False
                if create_host['epp']['response']['result']['@code'] != '1000':
                    raise EPPCommandFailed('EPP host_create failed with error code: %s' % (
                        create_host['epp']['response']['result']['@code'], ))
    if not update_domain:
        return True
    if not to_be_added and not to_be_removed:
        return False
    #--- UPDATE DOMAIN HOSTS
    update = epp_client.cmd_domain_update(
        domain,
        add_nameservers_list=to_be_added,
        remove_nameservers_list=to_be_removed,
    )
    if update['epp']['response']['result']['@code'] != '1000':
        raise EPPCommandFailed('EPP domain_update failed with error code: %s' % (
            update['epp']['response']['result']['@code'], ))
    return True

#------------------------------------------------------------------------------

def domain_set_auth_info(domain, auth_info=None):
    if not auth_info:
        auth_info = users.generatePassword()
    #--- UPDATE DOMAIN AUTH INFO
    update = epp_client.cmd_domain_update(
        domain,
        auth_info=auth_info,
    )
    if update['epp']['response']['result']['@code'] != '1000':
        raise EPPCommandFailed('EPP domain_update failed with error code: %s' % (
            update['epp']['response']['result']['@code'], ))
    return auth_info

#------------------------------------------------------------------------------

def domain_transfer_request(domain, auth_info):
    #--- SEND DOMAIN TRANSFER REQUEST
    transfer = epp_client.cmd_domain_transfer(domain, op='request', auth_info=auth_info)
    if transfer['epp']['response']['result']['@code'] != '1000':
        raise EPPCommandFailed('EPP domain_transfer failed with error code: %s' % (
            transfer['epp']['response']['result']['@code'], ))
    return True

#------------------------------------------------------------------------------

def domain_check_create_update_renew(domain, dform={},
                                     local_sync=True,
                                     create_contacts=True,
                                     create_nameservers=True,
                                     renew_years=None,
                                     verify_owner=True):
    #--- CHECK DOMAIN EXIST
    check = epp_client.cmd_domain_check([domain, ], )
    if check['epp']['response']['result']['@code'] != '1000':
        raise EPPCommandFailed('EPP domain_check failed with error code: %s' % (
            check['epp']['response']['result']['@code'], ))
    domain_exist = True
    if check['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '1':
        domain_exist = False
    else:
        if not check['epp']['response']['resData']['chkData']['cd']['reason'].startswith('(00)'):
            raise EPPCommandFailed('EPP domain_check failed with reason: %s' % (
                check['epp']['response']['resData']['chkData']['cd']['reason'], ))
    if verify_owner and domain_exist:
        epp_domain_info = read_domain_epp_info(domain) or {}
        auth_info = None
        if 'registrant' in epp_domain_info:
            auth_info = epp_domain_info['registrant']['pw']
    #--- GET EXISTING DOMAIN INFO
        exist_info = epp_client.cmd_domain_info(domain, auth_info=auth_info)
        if exist_info['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP domain_info failed with error code: %s' % (
                exist_info['epp']['response']['result']['@code'], ))
        if 'registrant' in epp_domain_info:
            if exist_info['epp']['response']['resData']['infData'].get('registrant', None) != epp_domain_info['registrant']['id']:
                raise EPPCommandInvalid('domain %s belongs to another registrant' % domain)
    if not dform:
        dform = {}
        fin = open(domains.domainPath(domain), 'r')
        domains.readform(dform, fin)
        fin.close()
    contacts_ids = {}
    if create_contacts:
    #--- CHECK CREATE UPDATE CONTACTS
        try:
            contacts_ids_or_errors = contacts_check_create_update(
                domain, dform, create_registrant=True, update_domain=False, local_sync=local_sync)
        except Exception as exc:
            return [exc, ]
        if isinstance(contacts_ids_or_errors, list):
            return contacts_ids_or_errors
        contacts_ids.update(contacts_ids_or_errors)
        contacts_ids.pop('registrant', None)
    #--- CHECK CREATE NAMESERVERS
    new_nameservers = domains.getNameServers(dform)
    if create_nameservers:
        nameservers_check_create_update(domain, new_servers=new_nameservers, update_domain=False)
    epp_domain_info = read_domain_epp_info(domain) or {}
    if not domain_exist and renew_years is not None:
    #--- CREATE DOMAIN HERE !!!!!!!!!!!!!!!
        if renew_years == -1:
            # initial load scenario
            formDate = dform['1b.']
            if not formDate:
                # expiration date not set ?
                formDate = formatdate(time.time() + 60 * 60 * 24 * 365 * 2, localtime=True)
            formDate = parsedate(formDate)
            if formDate is None:
                raise EPPCommandInvalid('expiration date for domain %s set incorrectly' % domain)
            formDate = datetime.datetime.fromtimestamp(time.mktime(formDate))
            days_difference = (formDate - datetime.datetime.now()).days
        else:
            days_difference = 365 * renew_years
        if days_difference > 365 * 10 - 1:
            # extension period must be no more than 10 years
            days_difference = 365 * 10 - 1
        if days_difference % 365 == 0:
            _period_units = 'y'
            _period_value = str(int(days_difference / 365.0))
        else:
            _period_units = 'd'
            _period_value = str(days_difference)
        create = epp_client.cmd_domain_create(
            domain=domain,
            nameservers=new_nameservers,
            contacts_dict={k: v[0] for k, v in contacts_ids.items()},
            registrant=epp_domain_info['registrant']['id'],
            # auth_info=epp_domain_info['registrant']['pw'],
            period=_period_value,
            period_units=_period_units,
        )
        if create['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP domain_create failed with error code: %s' % (
                create['epp']['response']['result']['@code'], ))
        epp_domain_info['name'] = domain
        epp_domain_info['svTRID'] = create['epp']['response']['trID']['svTRID']
        epp_domain_info['crDate'] = create['epp']['response']['resData']['creData']['crDate']
        epp_domain_info['exDate'] = create['epp']['response']['resData']['creData']['exDate']
        if local_sync:
            write_domain_epp_info(domain, epp_domain_info)
    auth_info = None
    if 'registrant' in epp_domain_info:
        auth_info = epp_domain_info['registrant']['pw']
    #--- GET DOMAIN INFO AGAIN
    info = epp_client.cmd_domain_info(domain, auth_info=auth_info)
    if info['epp']['response']['result']['@code'] != '1000':
        raise EPPCommandFailed('EPP domain_info failed with error code: %s' % (
            info['epp']['response']['result']['@code'], ))
    if 'registrant' in epp_domain_info:
        if info['epp']['response']['resData']['infData'].get('registrant', None) != epp_domain_info['registrant']['id']:
            raise EPPCommandInvalid('domain %s belongs to another registrant' % domain)
    #--- PREPARE CONTACTS
    try:
        current_contacts = info['epp']['response']['resData']['infData']['contact']
    except:
        current_contacts = []
    if not isinstance(current_contacts, list):
        current_contacts = [current_contacts, ]
    current_contacts = [{'type': i['@type'], 'id': i['#text']} for i in current_contacts]
    new_contacts = []
    for role in ['admin', 'tech', 'billing', ]:
        epp_info = epp_domain_info.get('contact_' + role, {})
        if epp_info:
            new_contacts.append({'type': role, 'id': epp_info.get('id', None)})
    add_contacts = []
    remove_contacts = []
    for new_cont in new_contacts:
        if new_cont['id'] not in [old_contact['id'] for old_contact in current_contacts]:
            add_contacts.append(new_cont)
    for old_cont in current_contacts:
        if old_cont['type'] == 'registrant':
            continue
        if old_cont['id'] not in [new_cont['id'] for new_cont in new_contacts]:
            remove_contacts.append(old_cont)
            epp_domain_info.pop('contact_' + old_cont['type'], None)
    #--- PREPARE NAMESERVERS
    try:
        current_nameservers = info['epp']['response']['resData']['infData']['ns']['hostObj']
    except:
        current_nameservers = []
    if not isinstance(current_nameservers, list):
        current_nameservers = [current_nameservers, ]
    remove_nameservers = []
    add_nameservers = []
    for old_server in current_nameservers:
        if old_server not in new_nameservers:
            remove_nameservers.append(old_server)
    for new_server in new_nameservers:
        if new_server not in current_nameservers:
            add_nameservers.append(new_server)
    if add_contacts or remove_contacts or add_nameservers or remove_nameservers:
    #--- UPDATE DOMAIN
        update = epp_client.cmd_domain_update(
            domain,
            add_nameservers_list=add_nameservers,
            remove_nameservers_list=remove_nameservers,
            add_contacts_list=add_contacts,
            remove_contacts_list=remove_contacts,
        )
        if update['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP domain_update failed with error code: %s' % (
                update['epp']['response']['result']['@code'], ))
        if local_sync:
            write_domain_epp_info(domain, epp_domain_info)
    currentEppDate = info['epp']['response']['resData']['infData']['exDate']
    eppDate = datetime.datetime.strptime(currentEppDate, '%Y-%m-%dT%H:%M:%S.%fZ')
    formDate = dform['1b.']
    if not formDate:
        formDate = formatdate(time.time(), True)
    formDate = parsedate(formDate)
    if formDate is None:
        raise EPPCommandInvalid('current expiration date for domain %s is unknown' % domain)
    renew_result = None
    if renew_years is not None and renew_years != -1:
        formDate = datetime.datetime.fromtimestamp(time.mktime(formDate))
        days_difference = 365 * renew_years
        if days_difference < 365 * 2:
            # extension period must be at least 2 years
            days_difference = 365 * 2
        if days_difference > 365 * 10 - 1:
            # extension period must be no more than 10 years
            days_difference = 365 * 10 - 1
        _newDate = formDate + datetime.timedelta(days=days_difference)
        if eppDate > _newDate:
            return []  # no need to renew because EPP date is greater than requested date
        if days_difference % 365 == 0:
            _period_units = 'y'
            _period_value = str(int(days_difference / 365.0))
        else:
            _period_units = 'd'
            _period_value = str(days_difference)
    #--- RENEW DOMAIN
        renew = epp_client.cmd_domain_renew(
            domain,
            cur_exp_date=currentEppDate,
            period=_period_value,
            period_units=_period_units,
        )
        if renew['epp']['response']['result']['@code'] != '1000':
            raise EPPCommandFailed('EPP domain_renew failed with error code: %s' % (
                renew['epp']['response']['result']['@code'], ))
        renew_result = renew['epp']['response']['resData']['renData']
    #--- LOCAL SYNC
    if local_sync:
        if renew_result:
            epp_domain_info['exDate'] = renew_result['exDate']
            write_domain_epp_info(domain, epp_domain_info)
        newFormDate = datetime.datetime.strptime(epp_domain_info['exDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        dform['1b.'] = formatdate(time.mktime(newFormDate.timetuple()), True)
        res = domains.domainPath(domain)
        if res:
            fout = open(res + '.tmp', 'w')
            domains.printform(dform, fout)
            os.fsync(fout)
            fout.close()
            os.rename(res + '.tmp', res)
            domain_contacts = domains.getDomainContactsDict(domain, dform)
            for role, contact_role_info in domain_contacts.items():
                users.addUserDomain(contact_role_info['email'], dform['2.'].lower(), dform['1b.'])
    return []

#------------------------------------------------------------------------------

def domain_regenerate(domain, dry_run=True, do_backup=True):
    """
    Change domain form file in /whois/ai/*
    Change user index in /index_domains/*
    Change info in /epp_domains/* only of domain name is missed in the file
    """
    errors = []
    domain_form_modified = False
    epp_info_modified = False
    #--- CHECK DOMAIN EXIST
    check = epp_client.cmd_domain_check([domain, ], )
    if check['epp']['response']['result']['@code'] != '1000':
        errors.append('failed to verify domain "%s" status' % domain)
        return errors
    domain_exist = True
    if check['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '1':
        domain_exist = False
    else:
        if not check['epp']['response']['resData']['chkData']['cd']['reason'].startswith('(00)'):
            errors.append('EPP domain_check failed with reason: %s' % (
                check['epp']['response']['resData']['chkData']['cd']['reason'], ))
            return errors
    if not domain_exist:
        errors.append('domain not exist on EPP')
        return errors
    #--- GET DOMAIN INFO
    auth_info = None
    exist_info = epp_client.cmd_domain_info(domain, auth_info=auth_info, raise_for_result=False)
    if exist_info['epp']['response']['result']['@code'] == '2201':
        errors.append('domain belongs to another registrar')
        return errors
    if exist_info['epp']['response']['result']['@code'] != '1000':
        errors.append('EPP response: ' + str(exist_info['epp']['response']['result']))
        return errors
    # epp_domain_path = os.path.join(epp_domains_dir, domain)
    epp_domain_info = read_domain_epp_info(domain) or {}
    if not epp_domain_info:
        errors.append('epp domain info not found')
        return errors
    if 'name' not in epp_domain_info or epp_domain_info['name'] != domain:
        if dry_run:
            errors.append('missed domain name in epp info file')
            return errors
        epp_domain_info['name'] = domain
        epp_info_modified = True
    if 'registrant' not in epp_domain_info or 'id' not in epp_domain_info['registrant'] or 'pw' not in epp_domain_info['registrant']:
        errors.append('registrant credentials not found')
        return errors
    if exist_info['epp']['response']['resData']['infData'].get('registrant', None) != epp_domain_info['registrant']['id']:
    #--- DOMAIN HAVE ANOTHER OWNER, ERROR
        errors.append('domain owns by another registrant')
        return errors
    #--- TEST REGISTRANT AUTH KEY
    exist_info = epp_client.cmd_domain_info(domain, auth_info=epp_domain_info['registrant']['pw'], raise_for_result=False)
    if exist_info['epp']['response']['result']['@code'] == '2201':
        errors.append('authorization faild, registrant password not match')
        return errors
    if exist_info['epp']['response']['result']['@code'] != '1000':
        errors.append('EPP response: ' + str(exist_info['epp']['response']['result']))
        return errors
    #--- READ FULL DOMAIN INFO
    try:
        real_epp_info = domain_get_full_info(domain, auth_info=epp_domain_info['registrant']['pw'])
    except (EPPCommandInvalid, EPPCommandFailed) as e:
        errors.append(str(e))
        return errors
    dform_real = domains.build_epp_form(real_epp_info)
    domain_path = domains.domainPath(domain)
    if not domain_path or not os.path.isfile(domain_path):
        if dry_run:
            errors.append('domain form file not exist')
            return errors
        dform_new = {}
        for field in domains.formfields():
            dform_new[field] = ''
        dform_new['1a.'] = 'not_paid'
        dform_new['1b.'] = formatdate(time.time(), True)
        dform_new['2.'] = domain
        domains.write2logDir(dform_new)
        fout = open(domain_path + '.tmp', 'w')
        domains.printform(dform_new, fout)
        os.fsync(fout)
        fout.close()
        os.rename(domain_path + '.tmp', domain_path)
    dform_current = {}
    fin = open(domain_path, 'r')
    domains.readform(dform_current, fin)
    fin.close()
    #--- COMPARE EXPIRY DATE
    if dform_current['1a.'] == 'not_paid':
        if dry_run:
            errors.append('domain wrongly marked as not_paid')
            return errors
        dform_current['1a.'] = ''
        dform_real['1a.'] = ''
        domain_form_modified = True
    if dform_current['1b.'] != dform_real['1b.']:
        try:
            current_expiry_date = datetime.datetime.fromtimestamp(time.mktime(parsedate(dform_current['1b.'])))
        except:
            current_expiry_date = None
        try:
            real_expiry_date = datetime.datetime.fromtimestamp(time.mktime(parsedate(dform_real['1b.'])))
        except:
            real_expiry_date = None
        if current_expiry_date and real_expiry_date:
            dt = real_expiry_date - current_expiry_date
            dt_hours = float(dt.total_seconds()) / (60.0 * 60.0)
            if dt_hours >= 2 * 24:
        #--- domain expiry date not in sync
                if dry_run:
                    errors.append('domain expiry date not in sync for %s, real: %s, known: %s' % (
                        domain_path, real_expiry_date, current_expiry_date))
                    return errors
                dform_current['1b.'] = dform_real['1b.']
                domain_form_modified = True
    #--- COMPARE DOMAIN FIELDS
    for field in dform_real.keys():
        if field in ['1a.', '1c.', '1b.', ]:
            # dform_real[field] = dform_current.get(field, '')
            continue
        if field in ['3f.', '4i.', '5i.', '6i.', ] and not dform_real[field]:
            dform_real[field] = dform_current.get(field, '')
            domain_form_modified = True
            continue
        if dform_current.get(field, '') != '' and dform_real[field] == '':
            dform_real[field] = dform_current.get(field, '')
            domain_form_modified = True
            continue
        if dform_current.get(field, '') == '' and dform_real[field] == 'unknown':
            dform_real[field] = ''
            domain_form_modified = True
            continue
        if field not in dform_current:
            if dry_run:
                errors.append('field %s not present in domain form' % field)
                continue
            domain_form_modified = True
        if dform_real[field] != dform_current[field]:
            if dry_run:
                errors.append('field %s not in sync: "%s" != "%s"' % (
                    field, dform_current[field], dform_real[field], ))
                continue
            domain_form_modified = True
    if not errors and not domain_form_modified and not epp_info_modified:
        return []
    if dry_run:
        return errors
    if epp_info_modified:
        write_domain_epp_info(domain, epp_domain_info)
    if domain_form_modified:
        domains.write2logDir(dform_real)
        if do_backup:
    #--- DO BACKUP
            fd, _ = tempfile.mkstemp(
                prefix='{}.'.format(domain),
                dir=deleted_domains_path
            )
            os.write(fd, open(domain_path, 'r').read())
            os.close(fd)
    #--- WRITE DOMAIN FILES
        fout = open(domain_path + '.tmp', 'w')
        domains.printform(dform_real, fout)
        os.fsync(fout)
        fout.close()
        os.rename(domain_path + '.tmp', domain_path)
        if dform_real['4l.'].strip() != '':
            users.addUserDomain(dform_real['4l.'].strip(), domain)
        if dform_real['5l.'].strip() != '':
            users.addUserDomain(dform_real['5l.'].strip(), domain)
        if dform_real['6l.'].strip() != '':
            users.addUserDomain(dform_real['6l.'].strip(), domain)
    return []

#------------------------------------------------------------------------------

def domain_regenerate_from_csv_row(csv_row, headers, dry_run=True, do_backup=True):
    """
    Change domain form file in /whois/ai/*
    Change user index in /index_domains/*
    Change epp info in /epp_domains/*
    """
    epp_domain_info_modified = False
    errors = []
    try:
        csv_record = domains.split_csv_row(csv_row, headers)
        dform_csv = domains.build_csv_form(csv_row, headers)
        domain = dform_csv['2.']
    except Exception as exc:
        errors.append('failed processing csv record: ' + str(exc))
        return errors
    try:
        real_expiry_date = datetime.datetime.fromtimestamp(time.mktime(datetime.datetime.strptime(
            csv_record.get('expiry_date_4'), '%Y-%m-%d').timetuple()))
    except Exception as exc:
        errors.append('failed reading expiry date from csv record: ' + str(exc))
        return errors
    if domains.scanForDomain(domain) == 'error':
    #--- invalid domain name
        errors.append('invalid domain name')
        return errors
    domain_form_path = domains.domainPath(domain)
    is_exist = domain_form_path and os.path.isfile(domain_form_path)
    registrar_id = csv_record.get('registrar_id_9')
    if registrar_id != 'whois_ai':
    #--- record belong to another registrar
        errors.append('record belong to another registrar: ' + registrar_id)
        return errors
    real_registrant_contact_id = csv_record.get('registrant_contact_id_24')
    real_billing_contact_id = csv_record.get('billing_contact_id_39')
    real_admin_contact_id = csv_record.get('admin_contact_id_54')
    real_tech_contact_id = csv_record.get('tech_contact_id_69')
    epp_domain_path = os.path.join(epp_domains_dir, domain)
    epp_domain_info = read_domain_epp_info(domain) or {}
    try:
        known_epp_expiry_date = datetime.datetime.fromtimestamp(time.mktime(parsedate(epp_domain_info['exDate'])))
    except:
        known_epp_expiry_date = None
    known_registrant_id = None if 'registrant' not in epp_domain_info else epp_domain_info['registrant']['id']
    known_admin_contact_id = None if 'contact_admin' not in epp_domain_info else epp_domain_info['contact_admin']['id']
    known_billing_contact_id = None if 'contact_billing' not in epp_domain_info else epp_domain_info['contact_billing']['id']
    known_tech_contact_id = None if 'contact_tech' not in epp_domain_info else epp_domain_info['contact_tech']['id']
    if 'name' not in epp_domain_info or epp_domain_info['name'] != domain:
        if dry_run:
            errors.append('missed domain name in ' + epp_domain_path)
            return errors
        epp_domain_info['name'] = domain
        epp_domain_info_modified = True
    if 'registrant' not in epp_domain_info or 'id' not in epp_domain_info['registrant'] or 'pw' not in epp_domain_info['registrant']:
        if dry_run:
            errors.append('epp registrant credentials not found in ' + epp_domain_path)
            return errors
        epp_domain_info['registrant'] = {'pw': 'qwerty123456', 'id': real_registrant_contact_id, }
        epp_domain_info_modified = True
    if not known_tech_contact_id and not known_admin_contact_id and not known_billing_contact_id:
        if dry_run:
            errors.append('epp no contacts present in ' + epp_domain_path)
            return errors
        epp_domain_info['contact_admin'] = {'pw': 'qwerty123456', 'id': real_registrant_contact_id, }
        epp_domain_info_modified = True
    if 'exDate' not in epp_domain_info:
        if dry_run:
            errors.append('epp no exDate field present in ' + epp_domain_path)
            return errors
        epp_domain_info['exDate'] = time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', real_expiry_date.timetuple())
        epp_domain_info_modified = True
    if not is_exist:
        if dry_run:
    #--- domain not found
            errors.append('domain not found in ' + domains.domainPath(domain))
            return errors
        else:
    #--- create new domain
            do_domain_create(domain, dform=dform_csv, epp_info=epp_domain_info)
            # epp_domain_info = read_domain_epp_info(domain) or {}
            epp_domain_info_modified = True
    try:
        dform = {}
        fin = open(domain_form_path, 'r')
        domains.readform(dform, fin)
        fin.close()
    except:
    #--- failed to read domain info
        errors.append('failed to read domain info from ' + domain_form_path)
        return errors
    try:
        known_domain_expiry_date = datetime.datetime.fromtimestamp(time.mktime(parsedate(dform['1b.'])))
    except:
        known_domain_expiry_date = None
    if real_registrant_contact_id and known_registrant_id != real_registrant_contact_id:
    #--- epp registrant ID is not math with csv record
        if dry_run:
            errors.append('epp registrant ID is not math with csv record in %s : known is %s, real is %s' % (
                epp_domain_path, known_registrant_id, real_registrant_contact_id, ))
            return errors
        epp_domain_info_modified = True
        if 'registrant' not in epp_domain_info:
            epp_domain_info['registrant'] = {'id': '', 'pw': 'qwerty123456'}
        epp_domain_info['registrant']['id'] = real_registrant_contact_id
    if real_admin_contact_id and known_admin_contact_id != real_admin_contact_id:
    #--- epp admin ID is not math with csv record
        if dry_run:
            errors.append('epp admin contact ID is not math with csv record in %s : known is %s, real is %s' % (
                epp_domain_path, known_admin_contact_id, real_admin_contact_id, ))
            return errors
        epp_domain_info_modified = True
        if 'contact_admin' not in epp_domain_info:
            epp_domain_info['contact_admin'] = {'id': '', 'pw': 'qwerty123456'}
        epp_domain_info['contact_admin']['id'] = real_admin_contact_id
    if real_billing_contact_id and known_billing_contact_id != real_billing_contact_id:
    #--- epp billing ID is not math with csv record
        if dry_run:
            errors.append('epp billing contact ID is not math with csv record in %s : known is %s, real is %s' % (
                epp_domain_path, known_billing_contact_id, real_billing_contact_id, ))
            return errors
        epp_domain_info_modified = True
        if 'contact_billing' not in epp_domain_info:
            epp_domain_info['contact_billing'] = {'id': '', 'pw': 'qwerty123456'}
        epp_domain_info['contact_billing']['id'] = real_billing_contact_id
    if real_tech_contact_id and known_tech_contact_id != real_tech_contact_id:
    #--- epp tech ID is not math with csv record
        if dry_run:
            errors.append('epp tech contact ID is not math with csv record in %s : known is %s, real is %s' % (
                epp_domain_path, known_tech_contact_id, real_tech_contact_id, ))
            return errors
        epp_domain_info_modified = True
        if 'contact_tech' not in epp_domain_info:
            epp_domain_info['contact_tech'] = {'id': '', 'pw': 'qwerty123456'}
        epp_domain_info['contact_tech']['id'] = real_tech_contact_id
    if known_epp_expiry_date:
        dt = real_expiry_date - known_epp_expiry_date
        dt_hours = float(dt.total_seconds()) / (60.0 * 60.0)
        if dt_hours >= 2 * 24:
    #--- domain expiry date not in sync
            if dry_run:
                errors.append('domain epp expiry date not in sync for %s, real: %s, known: %s' % (
                    domain_form_path, real_expiry_date, known_epp_expiry_date))
                return errors
            epp_domain_info_modified = True
            epp_domain_info['exDate'] = time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', real_expiry_date.timetuple())
    if known_domain_expiry_date:
        dt = real_expiry_date - known_domain_expiry_date
        dt_hours = float(dt.total_seconds()) / (60.0 * 60.0)
        if dt_hours >= 2 * 24:
    #--- domain expiry date not in sync
            if dry_run:
                errors.append('domain form expiry date not in sync for %s, real: %s, known: %s' % (
                    domain_form_path, real_expiry_date, known_domain_expiry_date))
                return errors
            dform['1b.'] = formatdate(time.mktime(real_expiry_date.timetuple()), True)
    #--- compare domain form fields with csv
    for field in dform_csv.keys():
        if field in ['1a.', '1c.', '4c.', '5c.', '6c.', '3a.', '4d.', ]:
            # skip person name and few other organization fields
            continue
        if field in ['1b.', ]:
            # skip expiry date
            continue
        if field in ['4d.', '5d.', '6d.', ]:
            # skip org. name, it is populated with user email to epp.whois.ai by default
            continue
        if field in ['7a.', '8a.', '9a.', '10a.', ]:
            # skip nameservers
            continue
        if dform.get(field, '') != '' and dform_csv[field] == '':
            # skip empty fields from csv if currently have more info
            continue
        if dform.get(field, '') == '' and dform_csv[field] == 'unknown':
            # skip 'unknown' values
            continue
        if field in ['3f.', '4i.', '5i.', '6i.', ] and not dform.get(field):
            if not dry_run:
                # data fix 1 : update coutries from csv if empty
                dform[field] = dform_csv[field]
            continue
#         if field not in ['3f.', '4i.', '5i.', '6i.', ]:
#             # run data fix 1 : only change country codes
#             continue
        if field in ['4j.', '5j.', '6j.', ] and dform_csv[field] == '+12645815398' and dform.get(field, '') == '':
            continue
        if field not in dform:
            if dry_run:
                errors.append('field %s not present in domain form' % field)
                continue
            # data fix 2 : build non existing fields from csv
            dform[field] = dform_csv[field]
        if dform_csv[field] != dform[field]:
            if dry_run:
                errors.append('field %s not in sync: "%s" != "%s"' % (
                    field, dform[field], dform_csv[field], ))
                continue
            # data fix 3 : override field value from csv
            dform[field] = dform_csv[field]
    if errors and dry_run:
        return errors
    if epp_domain_info_modified:
    # data fix 4 : write epp domain info
        write_domain_epp_info(domain, epp_domain_info)
    if do_backup:
    #--- DO BACKUP
        domains.write2logDir(dform)
        if os.path.isfile(domain_form_path):
            fd, _ = tempfile.mkstemp(
                prefix='{}.'.format(domain),
                dir=deleted_domains_path
            )
            os.write(fd, open(domain_form_path, 'r').read())
            os.close(fd)
    #--- WRITE DOMAIN FILES
    fout = open(domain_form_path + '.tmp', 'w')
    domains.printform(dform, fout)
    os.fsync(fout)
    fout.close()
    os.rename(domain_form_path + '.tmp', domain_form_path)
    if dform['4l.'].strip() != '':
        users.addUserDomain(dform['4l.'].strip(), domain)
    if dform['5l.'].strip() != '':
        users.addUserDomain(dform['5l.'].strip(), domain)
    if dform['6l.'].strip() != '':
        users.addUserDomain(dform['6l.'].strip(), domain)
    return errors

#------------------------------------------------------------------------------

def domains_synchronize(domains_list, renew=False, fix_errors=False):
    domain_results = {}
    epp_errors = []
    for domain in domains_list:
        domain_results[domain] = []
    #--- READ LOCAL EPP DOMAIN INDO
        epp_domain_info = read_domain_epp_info(domain) or {}
        domain_contacts = domains.getDomainContactsDict(domain)
        domain_emails = []
        for cont in domain_contacts.values():
            if cont.get('email').strip():
                domain_emails.append(cont.get('email').strip())
        if 'registrant' in epp_domain_info:
            auth_info = epp_domain_info['registrant']['pw']
    #--- CHECK DOMAIN EXIST
        check = epp_client.cmd_domain_check([domain, ], )
        if check['epp']['response']['result']['@code'] != '1000':
            domain_results[domain].append('error, failed to verify domain status')
            epp_errors.append('failed to verify domain "%s" status' % domain)
            continue
        domain_exist = True
        if check['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '1':
            domain_exist = False
        else:
            if not check['epp']['response']['resData']['chkData']['cd']['reason'].startswith('(00)'):
                epp_errors.append('EPP domain_check failed with reason: %s' % (
                    check['epp']['response']['resData']['chkData']['cd']['reason'], ))
                domain_results[domain].append('error, domain_check failed')
                continue
        if not domain_exist:
    #--- DOMAIN UPDATE: NOT EXIST IN EPP
            domain_results[domain].append('updated to not-paid, not exist on EPP: ' + do_domain_update(
                domain, {'1a.': 'not_paid'}))
            continue
    #--- GET EXISTING DOMAIN INFO
        exist_info = epp_client.cmd_domain_info(domain, auth_info=auth_info, raise_for_result=False)
        if exist_info['epp']['response']['result']['@code'] == '2201':
    #--- DOMAIN UPDATE: 2201 response info
            domain_results[domain].append('updated to not-paid, domain info response code is 2201: ' + do_domain_update(
                domain, {'1a.': 'not_paid'}))
            continue
        if exist_info['epp']['response']['result']['@code'] != '1000':
            epp_errors.append(exist_info['epp']['response']['result'])
            continue
        if 'registrant' in epp_domain_info:
            if exist_info['epp']['response']['resData']['infData'].get('registrant', None) != epp_domain_info['registrant']['id']:
    #--- DELETE UPDATE: ANOTHER OWNER
                domain_results[domain].append('updated to not-paid, another owner: ' + do_domain_update(
                    domain, {'1a.': 'not_paid'}))
                continue
        renew_errors = []
    #--- CHECK CREATE UPDATE RENEW
        if renew:
            try:
                renew_errors = domain_check_create_update_renew(domain, renew_years=None)
            except EPPCommandInvalid as e:
                domain_results[domain].append('invalid epp command')
                epp_errors.append(str(e))
                if fix_errors:
                    for email in domain_emails:
                        users.removeUserDomain(email, domain)
            except EPPCommandFailed as e:
                domain_results[domain].append('epp command failed')
                epp_errors.append(str(e))
                if fix_errors:
                    for email in domain_emails:
                        users.removeUserDomain(email, domain)
            except epp_client.EPPResponseFailed as e:
                domain_results[domain].append('epp response failed: ' + str(e.message))
                epp_errors.append(str(e))
                if fix_errors:
                    for email in domain_emails:
                        users.removeUserDomain(email, domain)
            if renew_errors:
                domain_results[domain].append('epp renew error')
                epp_errors.extend(renew_errors)
            else:
                domain_results[domain].append('renew success')
    #--- UPDATE DOMAIN FORM FILE
        dform = {}
        fin = open(domains.domainPath(domain), 'r')
        domains.readform(dform, fin)
        fin.close()
        try:
            exDate = formatdate(time.mktime(datetime.datetime.strptime(
                exist_info['epp']['response']['resData']['infData']['exDate'],
                '%Y-%m-%dT%H:%M:%S.%fZ').timetuple()), localtime=True)
        except:
            domain_results[domain].append('response exDate unrecognized')
            epp_errors.extend(renew_errors)
            exDate = dform['1b.']  # do not change it
        if dform['1b.'] != exDate:
            dform['1b.'] = exDate
            domain_results[domain].append('exDate updated: %s' % dform['1b.'])
        else:
            domain_results[domain].append('exDate in sync')
        res = domains.domainPath(domain)
        if res:
            fout = open(res + '.tmp', 'w')
            domains.printform(dform, fout)
            os.fsync(fout)
            fout.close()
            os.rename(res + '.tmp', res)
            for email in domain_emails:
            # domain_contacts = domains.getDomainContactsDict(domain, dform)
            # for role, contact_role_info in domain_contacts.items():
                users.addUserDomain(email, dform['2.'].lower(), dform['1b.'])
        epp_domain_info['exDate'] = exist_info['epp']['response']['resData']['infData']['exDate']
        write_domain_epp_info(domain, epp_domain_info)
        domain_results[domain].append('OK!')
    return domain_results, epp_errors

#------------------------------------------------------------------------------


if __name__ == '__main__':
    if False:
        dform = {'3c.': 'asdf', '3a.': '', '4e.': '', '4k.': '', '6i.': '', '5i.': '', '4c.': 'test123', '5e.': '', '5a.': '', '3e.': '', '4a.': '', '4g.': '', '5b.': '', '5g.': '', '7a.': 'ns1.offshore.ai', '6g.': '', '6a.': '', '5d.': '', '10a.': '',
                 '6c.': '', '5k.': '', '4i.': '', '8b.': '', '0c.': '', '6k.': '', '6e.': '', '2.': 'veselin-test15.net.ai', '1a.': 'abc@gmail.com', '1c.': '', '0a.': '', '5c.': 'sdfsdf', '4f.': '', '4d.': '', '5f.': '', '6l.': '', '5h.': '',
                 '9a.': '', '4j.': '', '3f.': '', '4b.': '', '3d.': '', '3b.': '', '6f.': '', '6b.': '', '4h.': '', '5j.': '', '6h.': '', '5l.': 'xyz@gmail.com', '6j.': '', '7b.': '', '8a.': 'ns2.offshore.ai', '0b.': '', '4l.': 'abc@gmail.com',
                 '1b.': 'Fri, 20 Dec 2019 20:49:38 -0400', '6d.': '', }
        print domain_check_create_update_renew('veselin-test15.net.ai', dform=dform, renew_years=None)

    if False:
        print domain_get_full_info('veselin-test32.ai')

    if False:
        import csv
        csv_domains = csv.reader(open('./Domains3.csv'))
        csv_records = [d for d in csv_domains]
        csv_header = csv_records[0]
        for csv_record in csv_records[1:]:
            print csv_record[1], domain_regenerate_from_csv_row(csv_record, csv_header)
    if True:
        print domain_set_auth_info('testdomain.ai')
