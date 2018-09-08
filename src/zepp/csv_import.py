import logging

import datetime
import time

from email.utils import parsedate, formatdate

from pika.exceptions import AMQPError

from back import domains

from zepp import client
from zepp import exceptions


def split_csv_row(csv_row, headers):
    """
    {'Auth_Info_Password_2': '',
     'NameServer_12': 'dns2.netbreeze.net',
     'NameServer_13': 'ns2.offshore.ai',
     'NameServer_14': '',
     'NameServer_15': '',
     'NameServer_16': '',
     'NameServer_17': '',
     'NameServer_18': '',
     'NameServer_19': '',
     'NameServer_20': '',
     'NameServer_21': '',
     'NameServer_22': '',
     'NameServer_23': '',
     'address_1_32': '2b',
     'address_1_47': '',
     'address_1_62': '3e',
     'address_1_77': '',
     'address_2_33': '',
     'address_2_48': '',
     'address_2_63': '',
     'address_2_78': '',
     'address_3_34': '',
     'address_3_49': '',
     'address_3_64': '',
     'address_3_79': '',
     'admin_contact_id_54': 'vesell420937fvfp',
     'billing_contact_id_39': '',
     'city_35': '2c',
     'city_50': '',
     'city_65': '3f',
     'city_80': '',
     'country_38': 'AI',
     'country_53': '',
     'country_68': 'AI',
     'country_83': '',
     'create_date_3': '2017-12-15',
     'ds_rdata_8': '',
     'e-mail_26': 'vesellov@gmail.com',
     'e-mail_41': '',
     'e-mail_56': 'vesellov@gmail.com',
     'e-mail_71': '',
     'eppstatus_7': '',
     'expiry_date_4': '2024-04-29',
     'fax_30': '',
     'fax_45': '',
     'fax_60': '3k',
     'fax_75': '',
     'fax_ext._31': '',
     'fax_ext._46': '',
     'fax_ext._61': '',
     'fax_ext._76': '',
     'locks_6': '',
     'name_1': 'bitdust.ai',
     'name_25': 'vesellov@gmail.com',
     'name_40': '',
     'name_55': 'vesellov@gmail.com',
     'name_70': '',
     'organisation_27': '2a',
     'organisation_42': '',
     'organisation_57': '3d',
     'organisation_72': '',
     'phone_28': '12645815398',
     'phone_43': '',
     'phone_58': '3j',
     'phone_73': '',
     'phone_ext._29': '',
     'phone_ext._44': '',
     'phone_ext._59': '',
     'phone_ext._74': '',
     'postal_code_37': '2e',
     'postal_code_52': '',
     'postal_code_67': '3h',
     'postal_code_82': '',
     'registrant_contact_id_24': 'vesell420946idyr',
     'registrar_email_11': 'migrate@nic.ai',
     'registrar_id_9': 'whois_ai',
     'registrar_name_10': 'WHOIS AI Registrar',
     'roid_0': '276693_nic_ai',
     'state/province_36': '2d',
     'state/province_51': '',
     'state/province_66': '3g',
     'state/province_81': '',
     'status_5': 'domain_status_active',
     'tech_contact_id_69': ''}
    """
    csv_record = {}
    for field_index in range(len(csv_row)):
        field = csv_row[field_index]
        header = headers[field_index]
        item_id = header.replace(' ', '_') + '_' + str(field_index)
        if item_id not in csv_record:
            csv_record[item_id] = field
        else:
            logging.warn('warning, field already exist: %s', item_id)
    return csv_record


def build_csv_form(csv_row, headers):
    csv_record = split_csv_row(csv_row, headers)
    try:
        csv_expiry_date = formatdate(datetime.datetime.strptime(
            csv_record.get('expiry_date_4'),
            '%Y-%m-%d',
        ).timetuple(), True)
    except:
        csv_expiry_date = formatdate(time.time(), True)
    dform = {
        '1a.': '',
        '1b.': csv_expiry_date,
        '1c.': '',
        '2.': csv_record.get('name_1', ''),
        '3a.': csv_record.get('organisation_27', ''),
        '3b.': csv_record.get('address_1_32', ''),
        '3c.': csv_record.get('city_35', ''),
        '3d.': csv_record.get('state/province_36', ''),
        '3e.': csv_record.get('postal_code_37', ''),
        '3f.': csv_record.get('country_38', ''),
        '4c.': '',
        '4d.': csv_record.get('organisation_57', ''),
        '4e.': csv_record.get('address_1_62', ''),
        '4f.': csv_record.get('city_65', ''),
        '4g.': csv_record.get('state/province_66', ''),
        '4h.': csv_record.get('postal_code_67', ''),
        '4i.': csv_record.get('country_68', ''),
        '4j.': csv_record.get('phone_58', ''),
        '4k.': csv_record.get('fax_60', ''),
        '4l.': csv_record.get('e-mail_56', ''),
        '5c.': '',
        '5d.': csv_record.get('organisation_72', ''),
        '5e.': csv_record.get('address_1_77', ''),
        '5f.': csv_record.get('city_80', ''),
        '5g.': csv_record.get('state/province_81', ''),
        '5h.': csv_record.get('postal_code_82', ''),
        '5i.': csv_record.get('country_83', ''),
        '5j.': csv_record.get('phone_73', ''),
        '5k.': csv_record.get('fax_75', ''),
        '5l.': csv_record.get('e-mail_71', ''),
        '6c.': '',
        '6d.': csv_record.get('organisation_42', ''),
        '6e.': csv_record.get('address_1_47', ''),
        '6f.': csv_record.get('city_50', ''),
        '6g.': csv_record.get('state/province_51', ''),
        '6h.': csv_record.get('postal_code_52', ''),
        '6i.': csv_record.get('country_53', ''),
        '6j.': csv_record.get('phone_43', ''),
        '6k.': csv_record.get('fax_45', ''),
        '6l.': csv_record.get('e-mail_41', ''),
    }
    for i in range(4):
        nsfield = 'NameServer_1' + str(i + 2)
        dform[str(i + 7) + 'a.'] = csv_record.get(nsfield, '')
    return dform


def domain_regenerate_from_csv_row(csv_row, headers, wanted_registrar='whois_ai', dry_run=True, do_backup=True):
    """
    Change domain form file in /whois/ai/*
    Change user index in /index_domains/*
    Change epp info in /epp_domains/*
    """
    epp_domain_info_modified = False
    errors = []
    try:
        csv_record = split_csv_row(csv_row, headers)
        dform_csv = build_csv_form(csv_row, headers)
        domain = dform_csv['2.']
    except Exception as exc:
        errors.append('failed processing csv record: ' + str(exc))
        return errors
    if not domains.is_valid(domain):
    #--- invalid domain name
        errors.append('invalid domain name')
        return errors
    #--- lookup existing domain
    known_domain = domains.take(domain)
    is_exist = known_domain is not None
    try:
        real_expiry_date = datetime.datetime.fromtimestamp(time.mktime(datetime.datetime.strptime(
            csv_record.get('expiry_date_4'), '%Y-%m-%d').timetuple()))
    except Exception as exc:
        errors.append('failed reading expiry date from csv record: ' + str(exc))
        return errors
    registrar_id = csv_record.get('registrar_id_9')
    if wanted_registrar and registrar_id != wanted_registrar:
    #--- record belong to another registrar
        errors.append('record belong to another registrar: ' + registrar_id)
        return errors
    real_registrant_contact_id = csv_record.get('registrant_contact_id_24')
    real_billing_contact_id = csv_record.get('billing_contact_id_39')
    real_admin_contact_id = csv_record.get('admin_contact_id_54')
    real_tech_contact_id = csv_record.get('tech_contact_id_69')
    known_epp_expiry_date = None if not known_domain else known_domain.expire_date
    known_registrant_id = None if not known_domain else known_domain.registrant.epp_id
    known_admin_contact_id = None if not known_domain else known_domain.contact_admin.epp_id
    known_billing_contact_id = None if not known_domain else known_domain.contact_billing.epp_id
    known_tech_contact_id = None if not known_domain else known_domain.contact_tech.epp_id
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
        if field in ['4j.', '5j.', '6j.', ] and dform_csv.get(field, '').strip() == '0' and dform.get(field, '').strip() == '':
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
                dir=deleted_domains_path()
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


def load_from_csv(filename):
    import csv
    epp_domains = csv.reader(open(filename))
    count = 0
    headers = []
    for row in epp_domains:
        count += 1
        if count == 1:
            headers.extend(row)
            continue
        domain = row[1]
        print(domain)
        try:
            results = epp_master.domain_regenerate_from_csv_row(row, headers, dry_run=True)
        except:
            print 'ERROR processing csv record:'
            pprint.pprint(row)
            continue
        if results:
            print 'ERRORS:'
            print results
        else:
            print 'OK'
