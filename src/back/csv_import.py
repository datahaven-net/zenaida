import logging

import re
import datetime
import csv

from django.utils.timezone import make_aware

from zen import zcontacts
from zen import zusers
from zen import zdomains

logger = logging.getLogger(__name__)


def split_csv_row(csv_row, headers):
    """
    {
        'admin_address_1_62': 'unknown',
        'admin_address_2_63': '',
        'admin_address_3_64': '',
        'admin_city_65': 'unknown',
        'admin_contact_id_54': 'abcd20329663if',
        'admin_countrycode_68': 'GB',
        'admin_email_56': 'abcd@gmail.com',
        'admin_fax_60': '',
        'admin_fax_ext_61': '',
        'admin_name_55': 'Some Person',
        'admin_organisation_57': 'Agent Corp Limited',
        'admin_phone_58': '+12123415398',
        'admin_phone_ext._59': '',
        'admin_postalcode_67': 'postal code',
        'admin_state_province_66': 'unknown',
        'auth_info_password_2': '',
        'billing_address_1_47': 'unknown',
        'billing_address_2_48': '',
        'billing_address_3_49': '',
        'billing_city_50': 'unknown',
        'billing_contact_id_39': 'abcd203326efgh',
        'billing_countrycode_53': 'GB',
        'billing_email_41': 'efgh@gmail.com',
        'billing_fax_45': '',
        'billing_fax_ext_46': '',
        'billing_name_40': 'Another Person',
        'billing_organisation_42': 'Agent Corp Limited',
        'billing_phone_43': '+12123415398',
        'billing_phone_ext_44': '',
        'billing_postalcode_52': 'unknown',
        'billing_state_province_51': 'unknown',
        'create_date_3': '2017-12-16',
        'ds_rdata_8': '',
        'eppstatus_7': '',
        'expiry_date_4': '2020-04-26',
        'locks_6': '',
        'name_1': 'domain-name.com',
        'nameserver_10_21': '',
        'nameserver_11_22': '',
        'nameserver_12_23': '',
        'nameserver_1_12': 'ns1.someserver.com',
        'nameserver_2_13': 'ns2.someserver.com',
        'nameserver_3_14': '',
        'nameserver_4_15': '',
        'nameserver_5_16': '',
        'nameserver_6_17': '',
        'nameserver_7_18': '',
        'nameserver_8_19': '',
        'nameserver_9_20': '',
        'registrant_address_1_32': 'Street123',
        'registrant_address_2_33': '',
        'registrant_address_3_34': '',
        'registrant_city_35': 'SomeTown',
        'registrant_contact_id_24': 'abcd203342efgh',
        'registrant_countrycode_38': 'GB',
        'registrant_email_26': 'kuku@hotmail.net',
        'registrant_fax_30': '',
        'registrant_fax_ext_31': '',
        'registrant_name_25': 'lala@gmail.com',
        'registrant_organisation_27': 'Agent Org Limited',
        'registrant_phone_28': '+12987815398',
        'registrant_phone_ext_29': '',
        'registrant_postalcode_37': '1234 AB',
        'registrant_state_province_36': 'unknown',
        'registrar_email_11': 'registrar@gmail.com',
        'registrar_id_9': 'registrar_id',
        'registrar_name_10': 'Some Domain Registrar',
        'roid_0': '310961_nic_com',
        'status_5': 'domain_status_active',
        'tech_contact_id_69': 'xyz203311xcdq',
        'technical_address_1_77': 'unknown',
        'technical_address_2_78': '',
        'technical_address_3_79': '',
        'technical_city_80': 'unknown',
        'technical_countrycode_83': 'GB',
        'technical_email_71': 'xyz@gmail.com',
        'technical_fax_75': '',
        'technical_fax_ext_76': '',
        'technical_name_70': 'Third Person',
        'technical_organisation_72': 'Agent Off Limited',
        'technical_phone_73': '+12645987398',
        'technical_phone_ext_74': '',
        'technical_postalcode_82': 'unknown',
        'technical_state_province_81': 'unknown'
    }
    """
    csv_record = {}
    for field_index in range(len(csv_row)):
        field = csv_row[field_index]
        header = headers[field_index]
        item_id = header.lower().replace(' ', '_') + '_' + str(field_index)
        if item_id not in csv_record:
            csv_record[item_id] = field
        else:
            logging.warn('field already exist: %r', item_id)
    return csv_record


def get_csv_domain_info(csv_row, headers):
    csv_record = split_csv_row(csv_row, headers)
    info = dict(
        create_date=make_aware(datetime.datetime.strptime(csv_record.get('create_date_3'), '%Y-%m-%d', )),  # -
        expiry_date=make_aware(datetime.datetime.strptime(csv_record.get('expiry_date_4'), '%Y-%m-%d', )),  # 1b.
        name=csv_record.get('name_1', ''),                                                                  # 2.
    #--- registrant contact
        registrant=dict(
            person_name='',                                                         # -
            organization_name=csv_record.get('registrant_organisation_27', ''),     # 3a.
            address_street=csv_record.get('registrant_address_1_32', ''),           # 3b.
            address_city=csv_record.get('registrant_city_35', ''),                  # 3c.
            address_province=csv_record.get('registrant_state_province_36', ''),    # 3d.
            address_postal_code=csv_record.get('registrant_postalcode_37', ''),     # 3e.
            address_country=csv_record.get('registrant_countrycode_38', ''),        # 3f.
            contact_voice=re.sub('[^\d^\+^\.]', '', csv_record.get('registrant_phone_28', ''))[:17],        # -
            contact_fax=re.sub('[^\d^\+^\.]', '', csv_record.get('registrant_fax_30', ''))[:17],            # -
            contact_email=csv_record.get('registrant_email_26', '').lower(),        # -
        ),
    #--- admin contact
        admin=dict(
            person_name=csv_record.get('admin_name_55', ''),                        # -
            organization_name=csv_record.get('admin_organisation_57', ''),          # 4d.
            address_street=csv_record.get('admin_address_1_62', ''),                # 4e.
            address_city=csv_record.get('admin_city_65', ''),                       # 4f.
            address_province=csv_record.get('admin_state_province_66', ''),         # 4g.
            address_postal_code=csv_record.get('admin_postalcode_67', ''),          # 4h.
            address_country=csv_record.get('admin_countrycode_68', ''),             # 4i.
            contact_voice=re.sub('[^\d^\+^\.]', '', csv_record.get('admin_phone_58', ''))[:17],             # 4j.
            contact_fax=re.sub('[^\d^\+^\.]', '', csv_record.get('admin_fax_60', ''))[:17],                 # 4k.
            contact_email=csv_record.get('admin_email_56', '').lower(),             # 4l.
        ),
    #--- tech contact
        tech=dict(
            person_name=csv_record.get('technical_name_70', ''),                    # -
            organization_name=csv_record.get('technical_organisation_72', ''),      # 5d.
            address_street=csv_record.get('technical_address_1_77', ''),            # 5e.
            address_city=csv_record.get('technical_city_80', ''),                   # 5f.
            address_province=csv_record.get('technical_state_province_81', ''),     # 5g.
            address_postal_code=csv_record.get('technical_postalcode_82', ''),      # 5h.
            address_country=csv_record.get('technical_countrycode_83', ''),         # 5i.
            contact_voice=re.sub('[^\d^\+^\.]', '', csv_record.get('technical_phone_73', ''))[:17],         # 5j.
            contact_fax=re.sub('[^\d^\+^\.]', '', csv_record.get('technical_fax_75', ''))[:17],             # 5k.
            contact_email=csv_record.get('technical_email_71', '').lower(),         # 5l.
        ),
    #--- billing contact
        billing=dict(
            person_name=csv_record.get('billing_name_40', ''),                      # -
            organization_name=csv_record.get('billing_organisation_42', ''),        # 6d.
            address_street=csv_record.get('billing_address_1_47', ''),              # 6e.
            address_city=csv_record.get('billing_city_50', ''),                     # 6f.
            address_province=csv_record.get('billing_state_province_51', ''),       # 6g.
            address_postal_code=csv_record.get('billing_postalcode_52', ''),        # 6h.
            address_country=csv_record.get('billing_countrycode_53', ''),           # 6i.
            contact_voice=re.sub('[^\d^\+^\.]', '', csv_record.get('billing_phone_43', ''))[:17],           # 6j.
            contact_fax=re.sub('[^\d^\+^\.]', '', csv_record.get('billing_fax_45', ''))[:17],               # 6k.
            contact_email=csv_record.get('billing_email_41', '').lower(),           # 6l.
        ),
    #--- nameservers
        nameservers=[
            csv_record.get('nameserver_1_12', ''),                                  # 7a.
            csv_record.get('nameserver_2_13', ''),                                  # 8a.
            csv_record.get('nameserver_3_14', ''),                                  # 9a.
            csv_record.get('nameserver_4_15', ''),                                  # 10a.
        ]
    )
    return info


def prepare_domain_status(csv_domain_status, default_status='active'):
    return {
        'domain_status_active': 'active',
        'domain_status_suspended': 'suspended',
    }.get(csv_domain_status, default_status)


def prepare_domain_epp_statuses(csv_domain_status, default_epp_statuses={'ok': 'Active'}):
    return {
        'domain_status_active': {'ok': 'Active'},
        'domain_status_suspended': {'serverHold': 'Suspended automatically'},
    }.get(csv_domain_status, default_epp_statuses)


def check_contact_to_be_created(domain_name, known_epp_contact_id, real_epp_contact_id, real_owner):
    errors = []
    to_be_created = False
    if known_epp_contact_id:
        if known_epp_contact_id != real_epp_contact_id:
    #--- contact epp ID is not matching
            errors.append("epp registrant ID is not matching with csv record, known is %r, real is %r" % (
                known_epp_contact_id, real_epp_contact_id, ))
            to_be_created = True
        else:
            if not zcontacts.verify(
                epp_id=real_epp_contact_id,
                owner=real_owner,
            ):
    #--- contact info is not matching
                errors.append("epp registrant ID is found, but known info is not matching with csv record, known is %r, real is %r" % (
                    known_epp_contact_id, real_epp_contact_id, ))
                to_be_created = True
    else:
    #--- contact not exist
        to_be_created = True
    return errors, to_be_created


def domain_regenerate_from_csv_row(csv_row, headers, wanted_registrar='whois_ai', skip_failing_contacts=False, dry_run=True, log=None):
    """
    """
    if log is None:
        log = logger
    errors = []
    try:
        csv_record = split_csv_row(csv_row, headers)
        csv_info = get_csv_domain_info(csv_row, headers)
        domain = csv_info['name']
    except Exception as exc:
        errors.append('failed processing csv record: ' + str(exc))
        return errors

    if not zdomains.is_valid(domain):
    #--- invalid domain name
        errors.append('invalid domain name')
        return errors

    #--- lookup existing domain
    known_domain = zdomains.domain_find(domain)
    real_registrar_id = csv_record.get('registrar_id_9')

    if wanted_registrar and real_registrar_id != wanted_registrar:
    #--- belong to another registrar
        errors.append('csv record belongs to another registrar: %r' % real_registrar_id)
        return errors

    real_expiry_date = csv_info['expiry_date']
    real_create_date = csv_info['create_date']
    real_epp_id = csv_record.get('roid_0')
    real_status = csv_record.get('status_5')
    real_auth_key = csv_record.get('auth_info_password_2')
    real_registrant_contact_id = csv_record.get('registrant_contact_id_24')
    real_admin_contact_id = csv_record.get('admin_contact_id_54')
    real_tech_contact_id = csv_record.get('tech_contact_id_69')
    real_billing_contact_id = csv_record.get('billing_contact_id_39')
    real_registrant_email = csv_info['registrant']['contact_email']
    real_admin_email = csv_info['admin']['contact_email']
    real_tech_email = csv_info['tech']['contact_email']
    real_billing_email = csv_info['billing']['contact_email']
    real_nameservers = csv_info['nameservers']

    known_expiry_date = None
    known_create_date = None
    known_epp_id = None
    known_auth_key = None
    known_registrant_contact_id = None 
    known_admin_contact_id = None
    known_tech_contact_id = None
    known_billing_contact_id = None
    known_nameservers = ['', ] * 4

    new_domain = None
    new_registrant_contact = None
    new_admin_contact = None
    new_tech_contact = None
    new_billing_contact = None

    need_registrant = False
    need_admin_contact = False
    need_tech_contact = False
    need_billing_contact = False

    owner_account = zusers.find_account(real_registrant_email)
    if not owner_account:
        if dry_run:
            errors.append('account %r is not exist in local DB' % real_registrant_email)
            return errors
    #--- account check/create
        new_password = zusers.generate_password(length=10)
        owner_account = zusers.create_account(
            email=real_registrant_email,
            account_password=new_password,
            is_active=True,
            **csv_info['registrant'],
        )
        log.info('generated new account and password for %r : %r', real_registrant_email, new_password)

    if known_domain:
        known_expiry_date = known_domain.expiry_date
        known_create_date = known_domain.create_date
        known_epp_id = known_domain.epp_id
        known_auth_key = known_domain.auth_key
        known_registrant_contact_id = None if not known_domain.registrant else known_domain.registrant.epp_id
        known_admin_contact_id = None if not known_domain.contact_admin else known_domain.contact_admin.epp_id
        known_billing_contact_id = None if not known_domain.contact_billing else known_domain.contact_billing.epp_id
        known_tech_contact_id = None if not known_domain.contact_tech else known_domain.contact_tech.epp_id
        known_nameservers = known_domain.list_nameservers()

    if real_admin_contact_id or real_tech_contact_id or real_billing_contact_id:
        if known_domain:
            if not known_tech_contact_id and not known_admin_contact_id and not known_billing_contact_id:
                if dry_run:
                    errors.append('no contacts present for the known domain in csv record')
                    return errors
    else:
        errors.append('no contacts (with epp ID) provided for the domain in csv record')
        return errors

    # TODO: try to avoid creating multiple contacts for different domains.
    # if two contacts have equal details we can re-use first contact and skip other one
    # but this will require EPP call to update domain infor on COCCA...
    if real_registrant_contact_id:
    #--- registrant check
        _errs, need_registrant = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_registrant_contact_id,
            real_epp_contact_id=real_registrant_contact_id,
            real_owner=owner_account,
        )
        if dry_run:
            errors.extend(_errs)

    if real_admin_contact_id:
    #--- admin contact check
        _errs, need_admin_contact = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_admin_contact_id,
            real_epp_contact_id=real_admin_contact_id,
            real_owner=owner_account,
        )
        if dry_run:
            errors.extend(_errs)

    if real_tech_contact_id:
    #--- tech contact check
        _errs, need_tech_contact = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_tech_contact_id,
            real_epp_contact_id=real_tech_contact_id,
            real_owner=owner_account,
        )
        if dry_run:
            errors.extend(_errs)

    if real_billing_contact_id:
    #--- billing contact check
        _errs, need_billing_contact = check_contact_to_be_created(
            domain_name=domain,
            known_epp_contact_id=known_billing_contact_id,
            real_epp_contact_id=real_billing_contact_id,
            real_owner=owner_account,
        )
        if dry_run:
            errors.extend(_errs)

    if not dry_run:
        if need_registrant:
    #--- registrant create
            new_registrant_contact = zcontacts.registrant_create(
                epp_id=real_registrant_contact_id,
                owner=owner_account,
                **csv_info['registrant'],
            )
            # TODO: make sure contact was assigned to the domain
        else:
            zcontacts.registrant_update(
                epp_id=real_registrant_contact_id,
                **csv_info['registrant'],
            )
    
        if need_admin_contact:
    #--- admin contact create
            new_admin_contact = zcontacts.contact_create(
                epp_id=real_admin_contact_id,
                owner=owner_account,
                raise_owner_exist=not skip_failing_contacts,
                **csv_info['admin'],
            )
            # TODO: make sure contact was assigned to the domain
        else:
            if real_admin_contact_id and real_admin_email:
                zcontacts.contact_update(
                    epp_id=real_admin_contact_id,
                    **csv_info['admin'],
                )

        if need_tech_contact:
    #--- tech contact create
            new_tech_contact = zcontacts.contact_create(
                epp_id=real_tech_contact_id,
                owner=owner_account,
                raise_owner_exist=not skip_failing_contacts,
                **csv_info['tech'],
            )
            # TODO: make sure contact was assigned to the domain
        else:
            if real_tech_contact_id and real_tech_email:
                zcontacts.contact_update(
                    epp_id=real_tech_contact_id,
                    **csv_info['tech'],
                )
    
        if need_billing_contact:
    #--- billing contact create
            new_billing_contact = zcontacts.contact_create(
                epp_id=real_billing_contact_id,
                owner=owner_account,
                raise_owner_exist=not skip_failing_contacts,
                **csv_info['billing'],
            )
            # TODO: make sure contact was assigned to the domain
        else:
            if real_billing_contact_id and real_billing_email:
                zcontacts.contact_update(
                    epp_id=real_billing_contact_id,
                    **csv_info['billing'],
                )

        if not known_domain and (
            need_admin_contact or need_billing_contact or need_tech_contact ) and (
            not new_billing_contact and not new_tech_contact and not new_admin_contact):
    #--- at least one contact exists
            log.info('no valid contacts found for domain, inactive "admin" contact will be created from known registrant info')
            new_admin_contact = zcontacts.contact_create(
                epp_id=None,  # TODO: run sync for those domains after all.
                owner=owner_account,
                **csv_info['registrant'],  # will be created new "inactive" contact from registrant's info
            )

    if not known_domain:
        if dry_run:
    #--- domain not found
            errors.append('domain not exist in local DB')
            return errors
    #--- create new domain
        new_domain = zdomains.domain_create(
            domain_name=domain,
            owner=owner_account,
            expiry_date=real_expiry_date,
            create_date=real_create_date,
            epp_id=real_epp_id,
            status=prepare_domain_status(real_status),
            epp_statuses=prepare_domain_epp_statuses(real_status),
            auth_key=real_auth_key,
            registrar=real_registrar_id,
            registrant=new_registrant_contact,
            contact_admin=new_admin_contact,
            contact_tech=new_tech_contact,
            contact_billing=new_billing_contact,
            nameservers=real_nameservers,
        )

    if new_domain:
    #--- DONE, new domain created
        return []

    if known_expiry_date:
        dt = real_expiry_date - known_expiry_date
        dt_hours = float(dt.total_seconds()) / (60.0 * 60.0)
        if dt_hours >= 24:
    #--- domain expiry date not in sync
            if dry_run:
                errors.append('expiry date not in sync - known is %r, real date is %r' % (
                    known_expiry_date, real_expiry_date, ))
                return errors
            known_domain.expiry_date = real_expiry_date
            known_domain.save()
            log.debug('known expiry date updated to %r', real_expiry_date)
    else:
        if known_domain:
    #--- expiry date was not set
            if real_expiry_date:
                if dry_run:
                    errors.append('expiry date was not set, real is %r' % real_expiry_date)
                    return errors
                known_domain.expiry_date = real_expiry_date
                known_domain.save()
                log.debug('expiry date was not set, updated with new date %r', real_expiry_date)

    if known_create_date:
        dt = real_create_date - known_create_date
        dt_hours = float(dt.total_seconds()) / (60.0 * 60.0)
        if dt_hours >= 24:
    #--- domain create date not in sync
            if dry_run:
                errors.append('create date not in sync - known is %r, real date is %r' % (
                    known_create_date, real_create_date, ))
                return errors
            known_domain.create_date = real_create_date
            known_domain.save()
            log.debug('known create date updated to %r', real_create_date)
    else:
        if known_domain:
            if real_create_date:
    #--- create date was not set
                if dry_run:
                    errors.append('create date was not set, real date is %r' % real_create_date)
                    return errors
                known_domain.create_date = real_create_date
                known_domain.save()
                log.debug('create date was not set, update with new date %r', real_create_date)

    #--- check known epp_id
    if known_epp_id:
        if known_epp_id != real_epp_id:
            if dry_run:
                errors.append('epp ID not in sync - known is %r, real is %r' % (
                    known_epp_id, real_epp_id, ))
                return errors
            known_domain.epp_id = real_epp_id
            known_domain.save()
            log.debug('known epp ID updated with new value %r', real_epp_id)
    else:
        if real_epp_id:
            if known_domain:
                if dry_run:
                    errors.append('epp ID was not set, real value is %s' % real_epp_id)
                    return errors
                known_domain.epp_id = real_epp_id
                known_domain.save()
                log.debug('epp ID was not set, now updated with a new value %r', real_epp_id)

    #--- check auth_key
    if known_auth_key:
        if known_auth_key != real_auth_key:
            if dry_run:
                errors.append('auth_key not in sync - known is %r, but real value is %r' % (
                    known_auth_key, real_auth_key, ))
                return errors
            known_domain.auth_key = real_auth_key
            known_domain.save()
            log.debug('known auth_key updated with new value %r', real_auth_key)
    else:
        if real_auth_key:
            if known_domain:
                if dry_run:
                    errors.append('auth_key was not set, real value is %r' % (
                        real_auth_key, ))
                    return errors
                known_domain.auth_key = real_auth_key
                known_domain.save()
                log.debug('auth_key was not set, now updated with new value %r', real_auth_key)

    #--- check nameservers
    for i in range(4):
        if real_nameservers[i] != known_nameservers[i]:
            if dry_run:
                errors.append('nameserver at position %d not in sync, known is %r, real value is %r' % (
                    i, known_nameservers[i], real_nameservers[i], ))
                return errors

    #--- update nameservers
    if not dry_run:
        zdomains.update_nameservers(known_domain, real_nameservers)

    if errors and dry_run:
        return errors

    #--- DONE, existing domain updated
    return errors


def load_from_csv(filename, dry_run=True, registrar_epp_id=None, log=None):
    if log is None:
        log = logger
    from back.models.registrar import Registrar
    epp_domains = csv.reader(open(filename))
    count = 0
    headers = next(epp_domains)
    if not registrar_epp_id:
        wanted_registrar = Registrar.registrars.first()
        if wanted_registrar:
            registrar_epp_id = wanted_registrar.epp_id
    if not registrar_epp_id:
        registrar_epp_id = 'zenaida_ai'
    for row in epp_domains:
        count += 1
        domain = row[1]
        try:
            errors = domain_regenerate_from_csv_row(
                row,
                headers,
                wanted_registrar=registrar_epp_id,
                skip_failing_contacts=True,
                dry_run=dry_run,
                log=log,
            )
        except Exception:
            log.exception('%s failed processing\n' % domain)
            return -1
        if errors:
            log.error('%s errors:\n    %s\n', domain, ';'.join(errors))
        else:
            log.info('%s processed\n\n', domain)
    return count
