#!/usr/bin/python

import os
import sys
import socket
import glob
import time
import datetime
import re
import cgi
import json
import pprint

from email.utils import parsedate, formatdate
from time import strftime

#------------------------------------------------------------------------------

sys.path.append('/home/veselin/datahaven/whois/conf')
sys.path.append('/home/whois.ai/conf')

sys.path.append('/home/veselin/datahaven/whois/cgi-bin')
sys.path.append('/home/whois.ai/cgi-bin')

sys.path.append('/home/veselin/datahaven/whois/')
sys.path.append('/home/whois.ai/')

#------------------------------------------------------------------------------

from whois_conf import (
    whois_path,
    user_input_log_path,
    suspect_log_file_path,
    log_dir_path,
    prohibited_words,
    prescribed_words,
)

from whois_constants import (
    domain_dirs,
    domains1,
    fieldsNotForUser,
    labels,
    no_email_str,
)

from lib import iso_countries

#------------------------------------------------------------------------------

def getall(theform, nolist=False):
    """
    getdata from cgi form to dictonary
    """
    data = {}
    for field in theform.keys():
        if field == 'csv_file':
            continue
        if isinstance(theform[field], list):
            if not nolist:
                data[field] = theform.getlist(field)
            else:
                data[field] = theform.getfirst(field)
        else:
            data[field] = theform[field].value
    return data


def log_input(filename, data):
    """
    check input and make log
    """
    fout = open(user_input_log_path(), 'a')
    params = ''

    try:
        ip_addr = cgi.escape(os.environ.get('REMOTE_ADDR', '0.0.0.0'))
    except:
        ip_addr = ''

    try:
        params += json.dumps(data)
    except:
        for field in data.keys():
            try:
                params += field + '="' + str(data[field]) + '"&'
            except:
                params += field + '="' + 'unicode_error' + '"&'
    print >> fout, strftime('%Y %m %d %H:%M:%S') + ' (' + ip_addr + ') [' + filename + '] : ' + params + ''
    fout.close()

    suspect = False
    suspect_i = ''
    for i in data.keys():
        regexp = '^[\w\s\-\.\+\*\=\!\@\#\$\%\(\)\[\]\{\}\,\?\:\;\`\<\>]*$'
        try:
            if re.match(regexp, data[i]) is None:
                suspect = True
                try:
                    suspect_i += '\n[' + i + '] - [[[' + str(data[i]) + ']]]'
                except:
                    suspect_i += '\n[' + i + '] - [[[' + 'unicode_error' + ']]]'
        except:
            suspect_i += '\n[' + i + '] - [[[' + 'error' + ']]]'
    if suspect:
        fout = open(suspect_log_file_path(), 'a')
        ip_addr = cgi.escape(os.environ.get('REMOTE_ADDR', '0.0.0.0'))
        print >>fout, strftime('%Y %m %d %H:%M:%S') + ' (' + ip_addr + ') - [' + filename + '] :' + suspect_i
        fout.close()


def make_msg(msg, color='red'):
    return '<p align=center><font color=%s>%s</font></p>' % (color, msg)


def formfields():
    """
    generate fields for form dictionary
    """
    #        0    1    2    3    4    5    6    7    8    9    10
    tops = ("c", "c", "a", "f", "l", "l", "l", "b", "b", "a", "a", )
    for section in range(0, 10 + 1):
        for part in range(ord("a"), ord(tops[section]) + 1):
            field = str(section) + chr(part) + "."
            if (section == 2):
                field = "2."
            yield field


def domainPathList(whois_path=whois_path()):
    """
    return paths of all domain forms
    """
    for domain1 in domain_dirs:
        for domain2 in os.listdir(os.path.join(whois_path, domain1)):
            domain_path = os.path.join(whois_path, domain1, domain2)
            if os.path.isfile(domain_path) == 0:
                continue
            yield domain_path


def lookupDomainPath(query, whois_path=whois_path()):
    """
    return paths of all domains forms matching given query using system 'glob' method
    """
    for domain1 in domain_dirs:
        for domain_path in glob.glob(os.path.join(whois_path, domain1, query)):
            if not os.path.isfile(domain_path):
                continue
            yield domain_path


def domainsList(whois_path=whois_path()):
    """
    return all domain names
    """
    for domain1 in domain_dirs:
        for domain2 in os.listdir(os.path.join(whois_path, domain1)):
            domain_path = os.path.join(whois_path, domain1, domain2)
            if os.path.isfile(domain_path) == 0:
                continue

            dform = {}
            fin = open(domain_path, 'r')
            readform(dform, fin)
            fin.close()

            domain = dform.get('2.', '')
            if domain == '':
                continue

            yield domain


def printform(form, openfile, forUser=False, fullForm=True):
    """
    print correct form to open file
    """
    for field in formfields():
        if forUser and (field in fieldsNotForUser):
            continue
        if field in form:
            openfile.write(field + ' ' + labels[field] + ' ' + form[field] + '\n')
        elif fullForm:
            openfile.write(field + ' ' + labels[field] + '\n')


def printformS(form, forUser=False, fullForm=True):
    """
    print form to string
    """
    outstr = ''
    for field in formfields():
        if field == '2.':
            outstr += 'DOMAIN INFORMATION\n'
        if field == '3a.':
            outstr += 'Organization Using Domain Name\n'
        if field == '4a.':
            outstr += 'Administrative Contact\n'
        if field == '5a.':
            outstr += 'Technical Contact\n'
        if field == '6a.':
            outstr += 'Billing Contact\n'
        if field == '7a.':
            outstr += 'Nameservers\n'
        if forUser and (field in fieldsNotForUser):
            continue
        if field in form:
            field_ = field if not forUser else ''
            indent = ' ' if field != '2.' else ''
            outstr += field_ + indent + labels[field] + ' ' + form[field] + '\n'
        elif fullForm:
            field_ = field
            if forUser:
                field_ = ''
            outstr += field_ + ' ' + labels[field] + '\n'
    return outstr


def readform(form, openfile):
    """
    read form info from opened file
    """
    for field in formfields():
        form[field] = ''
    while (1):
        linenl = openfile.readline()       # get line
        if (len(linenl) == 0):             # if nothing more (should at least be a nl)
            break                        # break out of this while loop
        line = linenl.rstrip()             # remove trailing white space
        for field in formfields():
            if (line.startswith(field)):
                splist = line.split(":")
                if len(splist) < 2:
                    continue
                left = splist[0]
                right = line[len(left) + 1:]
                form[field] = right.strip()


def readformS(form, datastr):
    """
    read form from string
    """
    for field in formfields():
        form[field] = ''
    dlines = datastr.split('\n')
    for linenl in dlines:
        line = linenl.rstrip()  # remove trailing white space
        for field in formfields():
            if (line.startswith(field)):
                splist = line.split(":")
                if len(splist) < 2:
                    continue
                left = splist[0]
                right = line[len(left) + 1:]
                form[field] = right.strip()


def build_epp_form(epp_info):
    dform = {
        '1a.': '',
        '1b.': epp_info.get('exDate', ''),
        '1c.': epp_info.get('registrant', {}).get('name', ''),
        '2.': epp_info.get('name', ''),
        '3a.': epp_info.get('registrant', {}).get('org', ''),
        '3b.': epp_info.get('registrant', {}).get('street', ''),
        '3c.': epp_info.get('registrant', {}).get('city', ''),
        '3d.': epp_info.get('registrant', {}).get('sp', ''),
        '3e.': epp_info.get('registrant', {}).get('pc', ''),
        '3f.': epp_info.get('registrant', {}).get('cc', ''),
        '4c.': epp_info.get('admin', {}).get('name', ''),
        '4d.': epp_info.get('admin', {}).get('org', ''),
        '4e.': epp_info.get('admin', {}).get('street', ''),
        '4f.': epp_info.get('admin', {}).get('city', ''),
        '4g.': epp_info.get('admin', {}).get('sp', ''),
        '4h.': epp_info.get('admin', {}).get('pc', ''),
        '4i.': epp_info.get('admin', {}).get('cc', ''),
        '4j.': epp_info.get('admin', {}).get('voice', ''),
        '4k.': epp_info.get('admin', {}).get('fax', ''),
        '4l.': epp_info.get('admin', {}).get('email', ''),
        '5c.': epp_info.get('tech', {}).get('name', ''),
        '5d.': epp_info.get('tech', {}).get('org', ''),
        '5e.': epp_info.get('tech', {}).get('street', ''),
        '5f.': epp_info.get('tech', {}).get('city', ''),
        '5g.': epp_info.get('tech', {}).get('sp', ''),
        '5h.': epp_info.get('tech', {}).get('pc', ''),
        '5i.': epp_info.get('tech', {}).get('cc', ''),
        '5j.': epp_info.get('tech', {}).get('voice', ''),
        '5k.': epp_info.get('tech', {}).get('fax', ''),
        '5l.': epp_info.get('tech', {}).get('email', ''),
        '6c.': epp_info.get('billing', {}).get('name', ''),
        '6d.': epp_info.get('billing', {}).get('org', ''),
        '6e.': epp_info.get('billing', {}).get('street', ''),
        '6f.': epp_info.get('billing', {}).get('city', ''),
        '6g.': epp_info.get('billing', {}).get('sp', ''),
        '6h.': epp_info.get('billing', {}).get('pc', ''),
        '6i.': epp_info.get('billing', {}).get('cc', ''),
        '6j.': epp_info.get('billing', {}).get('voice', ''),
        '6k.': epp_info.get('billing', {}).get('fax', ''),
        '6l.': epp_info.get('billing', {}).get('email', ''),
    }
    for i in xrange(len(epp_info.get('hostnames', []))):
        dform[str(i + 7) + 'a.'] = epp_info.get('hostnames', [])[i]
    return dform


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
    for field_index in xrange(len(csv_row)):
        field = csv_row[field_index]
        header = headers[field_index]
        item_id = header.replace(' ', '_') + '_' + str(field_index)
        if item_id not in csv_record:
            csv_record[item_id] = field
        else:
            print 'warning, field already exist', item_id
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
    for i in xrange(4):
        nsfield = 'NameServer_1' + str(i + 2)
        dform[str(i + 7) + 'a.'] = csv_record.get(nsfield, '')
    return dform


def write2logDir(form, ldir=log_dir_path()):
    """
    write form to log file
    """
    prefix = strftime('%Y%m%d%H%M%S')
    fout = open(ldir + prefix + '.' + form['2.'], 'w')
    printform(form, fout)
    fout.close()


def writeEPPInfo2logDir(epp_info, domain=None, ldir=log_dir_path()):
    """
    write form to log file
    """
    prefix = strftime('%Y%m%d%H%M%S')
    fout = open(ldir + prefix + '.epp.' + str(epp_info.get('name', domain)), 'w')
    epp_info_raw = pprint.pformat(epp_info)
    fout.write(epp_info_raw)
    fout.close()


def getNSlist(form):
    """
    get NameServers dict from the form dictionary
    """
    nslist = {}
    if form.get('7a.', '').strip() != '':
        nslist['7a.'] = form['7a.'].strip().lower()
    if form.get('8a.', '').strip() != '':
        nslist['8a.'] = form['8a.'].strip().lower()
    if form.get('9a.', '').strip() != '':
        nslist['9a.'] = form['9a.'].strip().lower()
    if form.get('10a.', '').strip() != '':
        nslist['10a.'] = form['10a.'].strip().lower()
    return nslist


def getNameServers(form):
    """
    get NameServers dict from the form dictionary
    """
    nslist = set()
    if form.get('7a.', '').strip() != '' and checkDomainName(form.get('7a.', '').strip()):
        nslist.add(form['7a.'].strip().lower())
    if form.get('8a.', '').strip() != '' and checkDomainName(form.get('8a.', '').strip()):
        nslist.add(form['8a.'].strip().lower())
    if form.get('9a.', '').strip() != '' and checkDomainName(form.get('9a.', '').strip()):
        nslist.add(form['9a.'].strip().lower())
    if form.get('10a.', '').strip() != '' and checkDomainName(form.get('10a.', '').strip()):
        nslist.add(form['10a.'].strip().lower())
    return list(nslist)


def getCountryCode(country_label):
    if country_label.upper() in iso_countries.labels().keys():
        return country_label.upper()
    return iso_countries.codes().get(country_label.lower(), 'AI')


def getCountryLabel(country_code):
    if country_code.lower() in iso_countries.codes().keys():
        return country_code
    return iso_countries.labels().get(country_code, 'Anguilla')


def checkFixCountryCode(cc):
    cc = cc.replace('UK', 'GB')
    return cc


def getContacts(form):
    """
    get Contacts from form
    """
    contacts = {}
    if form.get('4l.', ''):
        contacts['4l.'] = {
            'email': form.get('4l.', ''),
        }
    return contacts


def getDomainContacts(domain, dform=None):
    r = []
    if not dform:
        dform = {}
        fin = open(domainPath(domain), 'r')
        readform(dform, fin)
        fin.close()
    for i in ['4', '5', '6', ]:
        if dform[i + 'l.'].strip():
            r.append(dform[i + 'l.'].strip())
    return r


def getDomainRegistrantInfoDict(domain, dform=None):
    if not dform:
        dform = {}
        fin = open(domainPath(domain), 'r')
        readform(dform, fin)
        fin.close()
    return {
        "email": "",
        "contacts": [{
            "name": dform['1c.'].strip(),
            "org": dform['3a.'].strip(),
            "address": {
                "street": [dform['3b.'].strip(), ],
                "city": dform['3c.'].strip(),
                "sp": dform['3d.'].strip(),
                "pc": dform['3e.'].strip(),
                "cc": dform['3f.'].strip(),
            },
        }, ],
    }


def getDomainContactsDict(domain, dform=None):
    r = {}
    if not dform:
        dform = {}
        fin = open(domainPath(domain), 'r')
        readform(dform, fin)
        fin.close()
    for i, role in {'4': 'admin', '5': 'tech', '6': 'billing', }.items():
        if dform[i + 'l.'].strip():
            c = {
                "email": dform[i + 'l.'].strip(),
                "contacts": [{
                    "name": dform[i + 'c.'].strip(),
                    "org": dform[i + 'd.'].strip(),
                    "address": {
                        "street": [dform[i + 'e.'].strip(), ],
                        "city": dform[i + 'f.'].strip(),
                        "sp": dform[i + 'g.'].strip(),
                        "pc": dform[i + 'h.'].strip(),
                        "cc": dform[i + 'i.'].strip(),
                    },
                }, ],
            }
            if dform[i + 'j.'].strip():
                c["voice"] = dform[i + 'j.'].strip()
            if dform[i + 'k.'].strip():
                c["fax"] = dform[i + 'k.'].strip()
            r[role] = c
    return r


def FixContactInfo(info):
    for i in xrange(len(info['contacts'])):
        c = info['contacts'][i]
        if not c['name']:
            try:
                c['name'] = info['email'].lower()  # info['email'].replace('@', '_').replace('.', '_')
            except:
                c['name'] = 'unknown person'
        if not c['org']:
            try:
                c['org'] = info['email'].lower()  # info['email'].replace('@', '_').replace('.', '_')
            except:
                c['org'] = 'unknown organization'
        if not c['address']['street']:
            c['address']['street'] = ['unknown', ]
        if not c['address']['street'][0]:
            c['address']['street'] = ['unknown', ]
        if not c['address']['city']:
            c['address']['city'] = 'unknown'
        if not c['address']['sp']:
            c['address']['sp'] = 'unknown'
        if not c['address']['pc']:
            c['address']['pc'] = 'unknown'
        # The postcode must be 16 characters or less in length
        c['address']['pc'] = c['address']['pc'][:16]
        if not c['address']['cc']:
            c['address']['cc'] = 'AI'
        if not (len(c['address']['cc']) == 2 and c['address']['cc'] == c['address']['cc'].upper()):
            c['address']['cc'] = getCountryCode(c['address']['cc'])
        else:
            c['address']['cc'] = checkFixCountryCode(c['address']['cc'])
        info['contacts'][i] = c
    return info


def checkForm(form, user, domain):
    """
    check correction of form. need at lest 1 e-mail, domain name, and 2 servers hostnames
    """
    from users import check_correct_email
    report = ''
    if form.get('2.', '').strip() == '':
        report += 'Need Domain name\n'
    elif form['2.'].strip().lower() != domain.strip().lower():
        report += 'At least one email must stay as: %s\n' % domain
    has_email = False
    right_email = False
    if form.get('4l.', '') != '':
        if not check_correct_email(form['4l.'], full_check=True):
            report += 'Incorrect email provided\n'
        has_email = True
        if user == form['4l.'].strip().lower():
            right_email = True
    if form.get('5l.', '') != '':
        if not check_correct_email(form['5l.'], full_check=True):
            report += 'Incorrect email provided\n'
        has_email = True
        if user == form['5l.'].strip().lower():
            right_email = True
    if form.get('6l.', '') != '':
        if not check_correct_email(form['6l.'], full_check=True):
            report += 'Incorrect email provided\n'
        has_email = True
        if user == form['6l.'].strip().lower():
            right_email = True
    if not has_email:
        report += 'Need to set your email address\n'
    if not right_email and user != 'god':
        report += 'One of the emails must be set to %s\n' % user
    nslist = getNSlist(form)
    have_7a = False
    have_8a = False
    for key, val in nslist.items():
        if key == '7a.':
            have_7a = True
        if key == '8a.':
            have_8a = True
        if not checkDomainName(val, parent=domain):
            report += 'Incorrect nameserver name: %s\n' % val
        else:
            try:
                socket.gethostbyname(val)
            except:
                report += "Can't find nameserver: %s\n" % val
    if not have_7a:
        report += 'Need primary nameserver\n'
    if not have_8a:
        report += 'Need secondary nameserver\n'
    non_ascii = False
    for field in form.keys():
        if field in fieldsNotForUser:
            continue
        try:
            form[field].decode('ascii')
        except:
            non_ascii = True
    if non_ascii:
        report += 'Please use only ASCII characters to fill the form fields\n'
    return report


def scanForEmail(email, whois_path=whois_path()):
    """
    scan all forms which belongs to given e-mail and return list of forms paths
    """
    email_ = email.strip().lower()
    index = []
    for domain_path in domainPathList(whois_path):
        if os.path.isfile(domain_path) == 0:
            continue
        if email_ == 'god':
            index.append(domain_path)
            continue
        fin = open(domain_path, 'r')
        domain_src = fin.read()
        fin.close()
        re_obj1 = re.compile(r"^[4,5,6]l\.\ +E\-Mailbox\.{18}\:(.*?)$", re.M | re.I )
        search_res1 = re_obj1.findall(domain_src)
        if search_res1 is None and email_ == no_email_str:
            index.append(domain_path)
            continue
        if search_res1 is not None:
            ok = False
            for search_str in search_res1:
                if email_ == search_str.strip().lower():
                    ok = True
            if ok:
                index.append(domain_path)
    return index


def listDomains(page_index=0, page_size=100, whois_path=whois_path()):
    """
    list domains with pagination
    """
    results = []
    pos = 0
    for domain_path in domainPathList(whois_path):
        if os.path.isfile(domain_path) == 0:
            continue
        if pos < page_index * page_size:
            pos += 1
            continue
        if pos >= (page_index + 1) * page_size:
            break
        results.append(domain_path)
        pos += 1
    return results


def searchDomain(query_string, whois_path=whois_path()):
    """
    search for domains
    """
    results = []
    tld = ''
    if query_string.count('.'):
        query_string, tld = splitDomainName(query_string)
        tld = tld.replace('.ai', '')
    for domain_path in lookupDomainPath(query_string, whois_path):
        if not os.path.isfile(domain_path):
            continue
        if tld and not domain_path.count('/%s/' % tld):
            continue
        results.append(domain_path)
    return results


def userDomains(email, whois_path=whois_path()):
    """
    return list of domains to user
    """
    domains_list = scanForEmail(email, whois_path)
    domains = []
    for domain in domains_list:
        if os.access(domain, os.F_OK) == 0:
            continue
        form = {}
        fin = open(domain, 'r')
        readform(form, fin)
        fin.close()
        if form['2.'].strip() != '':
            domains.append(form['2.'].lower())
    return domains


def checkDomainName(domain, parent=''):
    regexp = '^[\w\-\.]*$'
    regexp_IP = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'
    if re.match(regexp, domain) is None:
        return False
    if domain.startswith('-'):
        # -abcd.ai is not a valid name
        return False
    if domain.count('--'):
        # IDN domains are not allowed
        return False
    if len(domain) > 4 and domain.find('.') == 2 and domain[1] == '-':
        # x-.ai is not valid name
        return False
    if domain.count('-.'):
        # abcd-.ai is not a valid name
        return False
    if domain.startswith('.'):
        return False
    if domain.endswith('.'):
        return False
    if domain.count('_.'):
        return False
    if domain.startswith('_'):
        return False
    if re.match(regexp_IP, domain.strip()) is not None:
        return False
    if parent:
        if parent not in ['offshore.ai', 'aitia.ai', ]:
            if domain.count('.' + parent):
                return False
    return True


def splitDomainName(domain):
    """
    Split domain name by two parts: name, tld
    where "tld" can be : ai, off.ai, com.ai, net.ai
    """
    if domain.startswith('www.'):
        domain = domain.replace('www.', '')
    dparts = domain.split('.')
    if len(dparts) < 2:
        return domain, ''
    if len(dparts) > 3:
        return dparts[0], '.'.join(dparts[1:])
    lev1 = dparts[-1].strip()
    lev2 = dparts[-2].strip()
    lev3 = ''
    if len(dparts) > 2:
        lev3 = dparts[-3].strip()
    if lev3 == '':
        return lev2, lev1
    else:
        return lev3, lev2 + '.' + lev1


def domainPath(domain, whois_path=whois_path()):
    """
    get internet domain name (address) and return full domain path or '' if bad domain name
    """
    if not checkDomainName(domain):
        return ''
    dparts = domain.lower().split('.')
    if len(dparts) < 2 or len(dparts) > 3:
        return ''
    lev1 = dparts[-1].strip()
    lev2 = dparts[-2].strip()
    lev3 = ''
    if len(dparts) > 2:
        lev3 = dparts[-3].strip()
    if lev1 != 'ai':
        return ''
    if lev3 != '' and lev2 not in domains1:
        return ''
    if lev3 == '':
        return whois_path + lev1 + '/' + lev2
    else:
        return whois_path + lev2 + '/' + lev3


def domainFromPath(domain_path):
    head, domain = os.path.split(domain_path.rstrip('/'))
    head, tld = os.path.split(head.rstrip('/'))
    if tld in domains1:
        return domain + '.' + tld + '.ai'
    return domain + '.ai'


def scanForDomain(domain, whois_path=whois_path()):
    """
    looking for existing domain, return domain path, 'error' or 'free'
    """
    if not checkDomainName(domain):
        return 'error'
    dpath = domainPath(domain, whois_path)
    if dpath == '':
        return 'error'
    if not os.path.exists(dpath):
        return 'free'
    if not os.access(dpath, os.F_OK):
        return 'free'
    return dpath


def ownDomain(domain, email):
    dpath = scanForDomain(domain)
    if dpath == 'free' or dpath == 'error':
        return False
    dform = {}
    fin = open(dpath, 'r')
    readform(dform, fin)
    fin.close()
    for x in ['4l.', '5l.', '6l.']:
        if email.strip().lower() == dform.get(x, '').strip().lower():
            return True
    return False


def prohibitedDomain(domain):
    s = domain.lower()
    matches = []
    for words in prohibited_words():
        found = 0
        for w in words:
            if w.strip() and s.count(w):
                found += 1
        if found == len(words):
            matches.append(words)
    return matches


def prescribedDomain(domain):
    s = domain.lower()
    matches = []
    for words in prescribed_words():
        found = 0
        for w in words:
            if w.strip() and s.count(w):
                found += 1
        if found > 0:
            matches.append(words)
    return matches


def checkDomainType(domain, level):
    if not checkDomainName(domain):
        return False
    dparts = domain.lower().split('.')
    if len(dparts) < 2 or len(dparts) > 3:
        return False
    lev1 = dparts[-1].strip()
    lev2 = dparts[-2].strip()
    lev3 = ''
    if len(dparts) > 2:
        lev3 = dparts[-3].strip()
    if lev1 != 'ai':
        return False
    if lev3 != '' and lev2 not in domains1:
        return False
    if lev3 == '':
        return level == 'ai'
    return lev2 == level


def paid_time(form_or_value):
    if isinstance(form_or_value, dict):
        curtime = form_or_value['1b.']
    else:
        curtime = form_or_value
    if curtime == -1:
        return -1
    extractD = parsedate(curtime)
    if extractD is None:
        return -1
    return time.mktime(extractD)


def check_paid(field_1a, field_1b, check_time=False):
    extractD = parsedate(field_1b)
    if extractD is None:
        return False
    time_state = False
    paid_state = True
    currentYear = time.localtime()
    if int(extractD[0]) > int(currentYear[0]):
        time_state = True
    else:
        t_domain = datetime.datetime.fromtimestamp(time.mktime(extractD))
        t_now = datetime.datetime.fromtimestamp(time.time())
        dt = t_now - t_domain
        dt_min = float(dt.total_seconds()) / 60.0
        if dt_min <= 60:
            time_state = True
    if field_1a.strip().lower() == 'not_paid':
        paid_state = False
    if paid_state:
        return True
    if check_time:
        if time_state:
            return True
    return False


def seconds_to_time_left_string(seconds):
    """
    Using this method you can print briefly some period of time.

    This is my post on StackOverflow to share that:
    http://stackoverflow.com/questions/538666/python-format-timedelta-
    to-string/19074707#19074707
    """
    s = int(seconds)
    years = s // 31104000
    if years > 1:
        return '%d years' % years
    s = s - (years * 31104000)
    months = s // 2592000
    if years == 1:
        r = 'one year'
        if months > 0:
            r += ' and %d months' % months
        return r
    if months > 1:
        return '%d months' % months
    s = s - (months * 2592000)
    days = s // 86400
    if months == 1:
        r = 'one month'
        if days > 0:
            r += ' and %d days' % days
        return r
    if days > 1:
        return '%d days' % days
    s = s - (days * 86400)
    hours = s // 3600
    if days == 1:
        r = 'one day'
        if hours > 0:
            r += ' and %d hours' % hours
        return r
    s = s - (hours * 3600)
    minutes = s // 60
    seconds = s - (minutes * 60)
    if hours >= 6:
        return '%d hours' % hours
    if hours >= 1:
        r = '%d hours' % hours
        if hours == 1:
            r = 'one hour'
        if minutes > 0:
            r += ' and %d minutes' % minutes
        return r
    if minutes == 1:
        r = 'one minute'
        if seconds > 0:
            r += ' and %d seconds' % seconds
        return r
    if minutes == 0:
        return '%d seconds' % seconds
    if seconds == 0:
        return '%d minutes' % minutes
    return '%d minutes and %d seconds' % (minutes, seconds)


def check_expired(field_1b, field_1a=None):
    extractD = parsedate(field_1b)
    if extractD is None:
        return -1
    if field_1a and field_1a.strip().lower() == 'not_paid':
        return 2
    currentYear = time.localtime()
    if int(extractD[0]) > int(currentYear[0]):
        # already paid for at least one year or even more
        return 1
    t_domain = datetime.datetime.fromtimestamp(time.mktime(extractD))
    t_now = datetime.datetime.fromtimestamp(time.time())
    dt = t_now - t_domain
    dt_min = float(dt.seconds) / 60.0
    if dt_min <= 60:
        # only one hour left before the moment when gona be expired
        return 1
    return 0


def paid(form, check_time=False):
    curtime = form['1b.']
    extractD = parsedate(curtime)
    if extractD is None:
        return False

    time_state = False
    paid_state = True

    currentYear = time.localtime()
    if int(extractD[0]) > int(currentYear[0]):
        time_state = True
    else:
        t_domain = datetime.datetime.fromtimestamp(time.mktime(extractD))
        t_now = datetime.datetime.fromtimestamp(time.time())

        dt = t_now - t_domain
        dt_min = float(dt.total_seconds()) / 60.0

        if dt_min <= 60:
            time_state = True

    if form['1a.'].strip().lower() == 'not_paid':
        paid_state = False

    if paid_state:
        return True

    if check_time:
        if time_state:
            return True

    return False


def write_suspect_log(login, susp=''):
    fout = open(suspect_log_file_path(), 'a')
    ip_addr = cgi.escape(os.environ.get('REMOTE_ADDR', '0.0.0.0'))
    print >>fout, strftime('%Y %m %d %H:%M:%S') + ' (' + ip_addr + ') - {' + login + '} ' + susp
    fout.close()
    os.chmod(suspect_log_file_path(), 666)


def checkDomainOwner(dform, login):
    owner_pass = False

    if dform['4l.'].strip().lower() == login:
        owner_pass = True
    if dform['5l.'].strip().lower() == login:
        owner_pass = True
    if dform['6l.'].strip().lower() == login:
        owner_pass = True
    if login == 'god':
        owner_pass = True

    if not owner_pass:
        write_suspect_log(login, 'bad owner')
    return owner_pass
