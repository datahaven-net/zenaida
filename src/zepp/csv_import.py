import logging

import datetime
import csv

from back import domains
from back import contacts


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
        item_id = header.lower().replace(' ', '_') + '_' + str(field_index)
        if item_id not in csv_record:
            csv_record[item_id] = field
        else:
            logging.warn('warning, field already exist: %s', item_id)
    return csv_record


def get_csv_domain_info(csv_row, headers):
    csv_record = split_csv_row(csv_row, headers)
    info = dict(
        expiry_date=datetime.datetime.strptime(csv_record.get('expiry_date_4'), '%Y-%m-%d', ),  # 1b.
        create_date=datetime.datetime.strptime(csv_record.get('create_date_3'), '%Y-%m-%d', ),  # -
        name=csv_record.get('name_1', ''),                              # 2.
    #--- registrant contact
        registrant=dict(
            person_name='',                                             # -
            organization_name=csv_record.get('organisation_27', ''),    # 3a.
            address_street=csv_record.get('address_1_32', ''),          # 3b.
            address_city=csv_record.get('city_35', ''),                 # 3c.
            address_province=csv_record.get('state/province_36', ''),   # 3d.
            address_postal_code=csv_record.get('postal_code_37', ''),   # 3e.
            address_country=csv_record.get('country_38', ''),           # 3f.
            contact_voice=csv_record.get('phone_28', ''),               # -
            contact_fax=csv_record.get('fax_30', ''),                   # -
            contact_email=csv_record.get('e-mail_26', ''),              # -
        ),
    #--- admin contact
        admin=dict(
            person_name=csv_record.get('name_40', ''),                  # -
            organization_name=csv_record.get('organisation_57', ''),    # 4d.
            address_street=csv_record.get('address_1_62', ''),          # 4e.
            address_city=csv_record.get('city_65', ''),                 # 4f.
            address_province=csv_record.get('state/province_66', ''),   # 4g.
            address_postal_code=csv_record.get('postal_code_67', ''),   # 4h.
            address_country=csv_record.get('country_68', ''),           # 4i.
            contact_voice=csv_record.get('phone_58', ''),               # 4j.
            contact_fax=csv_record.get('fax_60', ''),                   # 4k.
            contact_email=csv_record.get('e-mail_56', ''),              # 4l.
        ),
    #--- tech contact
        tech=dict(
            person_name=csv_record.get('name_70', ''),                  # -
            organization_name=csv_record.get('organisation_72', ''),    # 5d.
            address_street=csv_record.get('address_1_77', ''),          # 5e.
            address_city=csv_record.get('city_80', ''),                 # 5f.
            address_province=csv_record.get('state/province_81', ''),   # 5g.
            address_postal_code=csv_record.get('postal_code_82', ''),   # 5h.
            address_country=csv_record.get('country_83', ''),           # 5i.
            contact_voice=csv_record.get('phone_73', ''),               # 5j.
            contact_fax=csv_record.get('fax_75', ''),                   # 5k.
            contact_email=csv_record.get('e-mail_71', ''),              # 5l.
        ),
    #--- billing contact
        billing=dict(
            person_name=csv_record.get('name_25', ''),                  # -
            organization_name=csv_record.get('organisation_42', ''),    # 6d.
            address_street=csv_record.get('address_1_47', ''),          # 6e.
            address_city=csv_record.get('city_50', ''),                 # 6f.
            address_province=csv_record.get('state/province_51', ''),   # 6g.
            address_postal_code=csv_record.get('postal_code_52', ''),   # 6h.
            address_country=csv_record.get('country_53', ''),           # 6i.
            contact_voice=csv_record.get('phone_43', ''),               # 6j.
            contact_fax=csv_record.get('fax_45', ''),                   # 6k.
            contact_email=csv_record.get('e-mail_41', ''),              # 6l.
        ),
    )
    return info


def check_contact_to_be_created(domain_name, known_epp_contact_id, real_epp_contact_id, real_email):
    errors = []
    to_be_created = False
    if known_epp_contact_id:
        if known_epp_contact_id != real_epp_contact_id:
    #--- contact epp ID is not matching
            errors.append('%s: epp registrant ID is not matching with csv record, known is %s, real is %s' % (
                domain_name, known_epp_contact_id, real_epp_contact_id, ))
            to_be_created = True
        else:
            if not contacts.verify(
                epp_id=real_epp_contact_id,
                email=real_email,
            ):
    #--- contact info is not matching
                errors.append('%s: epp registrant ID found, but known info is not matching with csv record, known is %s, real is %s' % (
                    domain_name, known_epp_contact_id, real_epp_contact_id, ))
                to_be_created = True
    else:
    #--- contact not exist
        to_be_created = True
    return errors, to_be_created


def domain_regenerate_from_csv_row(csv_row, headers, wanted_registrar='whois_ai', dry_run=True, do_backup=True):
    """
    """
    errors = []
    try:
        csv_record = split_csv_row(csv_row, headers)
        csv_info = get_csv_domain_info(csv_row, headers)
        domain = csv_info['name']
    except Exception as exc:
        errors.append('failed processing csv record: ' + str(exc))
        return errors
    if not domains.is_valid(domain):
    #--- invalid domain name
        errors.append('invalid domain name')
        return errors

    #--- lookup existing domain
    known_domain = domains.find(domain)
    real_expiry_date = csv_info['expiry_date']
    real_create_date = csv_info['create_date']
    real_registrar_id = csv_record.get('registrar_id_9')

    if wanted_registrar and real_registrar_id != wanted_registrar:
    #--- belong to another registrar
        errors.append('%s: csv record belongs to another registrar %s' % (domain, real_registrar_id, ))
        return errors

    real_registrant_contact_id = csv_record.get('registrant_contact_id_24')
    real_admin_contact_id = csv_record.get('admin_contact_id_54')
    real_tech_contact_id = csv_record.get('tech_contact_id_69')
    real_billing_contact_id = csv_record.get('billing_contact_id_39')
    real_registrant_email = csv_info['registrant']['contact_email']
    real_admin_email = csv_info['admin']['contact_email']
    real_tech_email = csv_info['tech']['contact_email']
    real_billing_email = csv_info['billing']['contact_email']

    real_auth_info_password = csv_record.get('auth_info_password_2')
    real_epp_id = csv_record.get('roid_0')

    known_expiry_date = None
    known_registrant_contact_id = None 
    known_admin_contact_id = None
    known_tech_contact_id = None
    known_billing_contact_id = None
    known_registrant_email = None
    known_admin_email = None
    known_tech_email = None
    known_billing_email = None

    new_domain = None
    new_registrant_contact = None
    new_admin_contact = None
    new_tech_contact = None
    new_billing_contact = None

    need_registrant = False
    need_admin_contact = False
    need_tech_contact = False
    need_billing_contact = False

    if known_domain:
        known_expiry_date = known_domain.expiry_date
        known_registrant_contact_id = None if not known_domain.registrant else known_domain.registrant.epp_id
        known_admin_contact_id = None if not known_domain.contact_admin else known_domain.contact_admin.epp_id
        known_billing_contact_id = None if not known_domain.contact_billing else known_domain.contact_billing.epp_id
        known_tech_contact_id = None if not known_domain.contact_tech else known_domain.contact_tech.epp_id
        known_registrant_email = None if not known_domain.registrant else known_domain.registrant.profile.account.email
        known_admin_email = None if not known_domain.contact_admin else known_domain.contact_admin.profile.account.email
        known_tech_email = None if not known_domain.contact_tech else known_domain.contact_tech.profile.account.email
        known_billing_email = None if not known_domain.contact_billing else known_domain.contact_billing.profile.account.email

    if real_admin_contact_id or real_tech_contact_id or real_billing_contact_id:
        if known_domain:
            if not known_tech_contact_id and not known_admin_contact_id and not known_billing_contact_id:
                if dry_run:
                    errors.append('%s: no contacts present for known domain' % domain)
                    return errors
    else:
        errors.append('%s: no csv contacts provided for domain' % domain)
        return errors

    if real_registrant_contact_id:
    #--- registrant check
        _errs, need_registrant = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_registrant_contact_id,
            real_epp_contact_id=real_registrant_contact_id,
            real_email=real_registrant_email,
        )
        if dry_run:
            errors.extend(_errs)

    if real_admin_contact_id:
    #--- admin contact check
        _errs, need_admin_contact = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_admin_contact_id,
            real_epp_contact_id=real_admin_contact_id,
            real_email=real_admin_email,
        )
        if dry_run:
            errors.extend(_errs)

    if real_tech_contact_id:
    #--- tech contact check
        _errs, need_tech_contact = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_tech_contact_id,
            real_epp_contact_id=real_tech_contact_id,
            real_email=real_tech_email,
        )
        if dry_run:
            errors.extend(_errs)

    if real_billing_contact_id:
    #--- billing contact check
        _errs, need_billing_contact = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_billing_contact_id,
            real_epp_contact_id=real_billing_contact_id,
            real_email=real_billing_email,
        )
        if dry_run:
            errors.extend(_errs)

    if not dry_run:
        if need_registrant:
    #--- registrant create
            new_registrant_contact = contacts.create(
                epp_id=real_registrant_contact_id,
                email=real_registrant_email,
                **csv_info['registrant'],
            )
        else:
            contacts.update(real_registrant_email, **csv_info['registrant'])
    
        if need_admin_contact:
    #--- admin contact create
            new_admin_contact = contacts.create(
                epp_id=real_admin_contact_id,
                email=real_admin_email,
                **csv_info['admin'],
            )
        else:
            contacts.update(real_admin_email, **csv_info['admin'])

        if need_tech_contact:
    #--- tech contact create
            new_tech_contact = contacts.create(
                epp_id=real_tech_contact_id,
                email=real_tech_email,
                **csv_info['tech'],
            )
        else:
            contacts.update(real_tech_email, **csv_info['tech'])
    
        if need_billing_contact:
    #--- billing contact create
            new_billing_contact = contacts.create(
                epp_id=real_billing_contact_id,
                email=real_billing_email,
                **csv_info['billing'],
            )
        else:
            contacts.update(real_billing_email, **csv_info['billing'])
    
    if not known_domain:
        if dry_run:
    #--- domain not found
            errors.append('%s: domain not exist' % domain)
            return errors
    #--- create new domain
        new_domain = domains.create(
            domain=domain,
            expiry_date=real_expiry_date,
            create_date=real_create_date,
            epp_id=real_epp_id,
            auth_key=real_auth_info_password,
            registrar=real_registrar_id,
            registrant=new_registrant_contact,
            contact_admin=new_admin_contact,
            contact_tech=new_tech_contact,
            contact_billing=new_billing_contact,
        )

    if known_expiry_date:
        dt = real_expiry_date - known_expiry_date
        dt_hours = float(dt.total_seconds()) / (60.0 * 60.0)
        if dt_hours >= 24:
    #--- domain expiry date not in sync
            if dry_run:
                errors.append('%s: expiry date not in sync for, known is %s, real is %s' % (
                    domain, known_expiry_date, real_expiry_date, ))
                return errors
            known_domain.expiry_date = real_expiry_date
            known_domain.save()
    else:
        if known_domain:
    #--- updated known expiry date
            known_domain.expiry_date = real_expiry_date
            known_domain.save()

    # TODO: create_date, nameservers

    if errors and dry_run:
        return errors

    return errors


def load_from_csv(filename):
    epp_domains = csv.reader(open(filename))
    count = 0
    headers = []
    for row in epp_domains:
        count += 1
        if count == 1:
            headers.extend(row)
            continue
        domain = row[1]
        try:
            errors = domain_regenerate_from_csv_row(row, headers, dry_run=True)
        except:
            logging.error('%s failed processing csv record: %r', domain, row)
            continue
        if errors:
            logging.error('%s errors: %r', domain, errors)
        else:
            logging.info('OK %s', domain)
