import logging

from back.models.contact import Contact, Registrant

from lib import iso_countries

logger = logging.getLogger(__name__)


def by_id(contact_id):
    """
    Return Contact object with given id or None.
    """
    if not contact_id:
        return None
    return Contact.contacts.get(id=contact_id)


def by_epp_id(epp_id):
    """
    Return Contact object with given epp_id or None.
    """
    if not epp_id:
        return None
    return Contact.contacts.filter(epp_id=epp_id).first()


def exists(epp_id):
    """
    Return `True` if contact with given epp_id exists, doing query in Contact table.
    """
    if not epp_id:
        return False
    return bool(Contact.contacts.filter(epp_id=epp_id).first())


def list_contacts(owner):
    """
    Returns list of contacts of given user.
    """
    return list(Contact.contacts.filter(owner=owner).all())


def verify(epp_id, email=None, owner=None):
    """
    Make sure that existing contact with given epp_id have same info.
    """
    if not exists(epp_id):
        return False
    cont = Contact.contacts.get(epp_id=epp_id)
    if email and cont.owner.email != email:
        return False
    if owner and cont.owner.pk != owner.pk:
        return False
    return True


def extract_address_info(contact_info_response):
    """
    From given contact info EPP response extracts address info into flat dictionary.   
    """
    d = contact_info_response['epp']['response']['resData']['infData']
    a = {}
    postal_info_list = d['postalInfo'] if isinstance(d['postalInfo'], list) else [d['postalInfo'], ]
    local_address = False
    for pi in postal_info_list:
        if pi['@type'] == 'loc':
            local_address = True
            a.update({
                'name': pi.get('name', ''),
                'org': pi.get('org', '') or '',
                'cc': pi.get('addr', {}).get('cc'),
                'city': pi.get('addr', {}).get('city'),
                'pc': pi.get('addr', {}).get('pc') or '',
                'sp': pi.get('addr', {}).get('sp') or '',
                'street': (' '.join(pi.get('addr', {}).get('street'))) if isinstance(
                    pi.get('addr', {}).get('street'), list) else pi.get('addr', {}).get('street'),
            })
            break
    if not local_address:
        for pi in postal_info_list:
            a.update({
                'name': pi.get('name', ''),
                'org': pi.get('org', '') or '',
                'cc': pi.get('addr', {}).get('cc'),
                'city': pi.get('addr', {}).get('city'),
                'pc': pi.get('addr', {}).get('pc') or '',
                'sp': pi.get('addr', {}).get('sp') or '',
                'street': (' '.join(pi.get('addr', {}).get('street'))) if isinstance(
                    pi.get('addr', {}).get('street'), list) else pi.get('addr', {}).get('street'),
            })
    return a


def contact_create(epp_id, owner, contact_info_response=None, **kwargs):
    """
    Creates new contact for given owner, but only if Contact with same epp_id not exist yet.
    """
    if epp_id:
        existing_contact = Contact.contacts.filter(epp_id=epp_id).first()
        if existing_contact:
            if existing_contact.owner.pk != owner.pk:
                raise Exception('Invalid owner, existing contact have another owner already')
            logger.debug('contact with epp_id=%s already exist', epp_id)
            return existing_contact
    if contact_info_response:
        d = contact_info_response['epp']['response']['resData']['infData']
        a = extract_address_info(contact_info_response)
        new_contact = Contact.contacts.create(
            epp_id=epp_id,
            owner=owner,
            person_name=a['name'],
            organization_name=a['org'],
            address_street=a['street'],
            address_city=a['city'],
            address_province=a['sp'],
            address_postal_code=a['pc'],
            address_country=a['cc'],
            contact_voice=str(d.get('voice', '')),
            contact_fax=str(d.get('fax', '')),
            contact_email=str(d['email']),
        )
        logger.info('contact created: %s', new_contact)
        return new_contact
    new_contact = Contact.contacts.create(epp_id=epp_id, owner=owner, **kwargs)
    logger.info('contact created: %s', new_contact)
    return new_contact


def contact_create_from_profile(owner, profile_object):
    """
    Creates a new Contact from existing Profile object. 
    """
    new_contact = Contact.contacts.create(
        owner=owner,
        person_name=profile_object.person_name,
        organization_name=profile_object.organization_name or '',
        address_street=profile_object.address_street,
        address_city=profile_object.address_city,
        address_province=profile_object.address_province or '',
        address_postal_code=profile_object.address_postal_code or '',
        address_country=profile_object.address_country,
        contact_voice=profile_object.contact_voice or '',
        contact_fax=profile_object.contact_fax or '',
        contact_email=profile_object.contact_email,
    )
    logger.info('contact created from existing profile: %s', new_contact)
    return new_contact


def contact_update(epp_id, **kwargs):
    """
    Update given Contact with new field values.
    """
    existing_contact = Contact.contacts.filter(epp_id=epp_id).first()
    if not existing_contact:
        raise Exception('Contact not found')
    updated = Contact.contacts.filter(pk=existing_contact.pk).update(**kwargs)
    logger.info('contact updated: %s', existing_contact)
    return updated


def contact_refresh(epp_id, contact_info_response):
    """
    Update given Contact with new field values.
    """
    existing_contact = Contact.contacts.filter(epp_id=epp_id).first()
    if not existing_contact:
        raise Exception('Contact not found')
    d = contact_info_response['epp']['response']['resData']['infData']
    a = extract_address_info(contact_info_response)
    updated = Contact.contacts.filter(pk=existing_contact.pk).update(
        person_name=a['name'],
        organization_name=a['org'],
        address_street=a['street'],
        address_city=a['city'],
        address_province=a['sp'],
        address_postal_code=a['pc'],
        address_country=a['cc'],
        contact_voice=str(d.get('voice', '')),
        contact_fax=str(d.get('fax', '')),
        contact_email=str(d['email']),
    )
    logger.info('contact refreshed: %s', existing_contact)
    return updated


def to_dict(contact_object):
    info = {
        'email': contact_object.contact_email,
        'contacts': [{
            'name': contact_object.person_name,
            'org': contact_object.organization_name,
            'address': {
                'street': [contact_object.address_street, ],
                'city': contact_object.address_city,
                'sp': contact_object.address_province,
                'pc': contact_object.address_postal_code,
                'cc': contact_object.address_country,
            },
        }, ],
    }
    if contact_object.contact_voice:
        info['voice'] = contact_object.contact_voice
    if not info.get('voice'):
        # every contact must have a voice number
        info['voice'] = '0'
    if contact_object.contact_fax:
        info['fax'] = contact_object.contact_fax
    else:
        info['fax'] = None
    c = info['contacts'][0]
    # Person name and Org name must be always present
    if not c['name']:
        c['name'] = info['email'].lower()
    if not c['org']:
        c['org'] = info['email'].lower()
    # Must be fully specified address details
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
    # The postal code must be 16 characters or less in length
    c['address']['pc'] = c['address']['pc'][:16]
    # TODO: detect default country based on current location
    known_country_code = 'GB'
    if not c['address']['cc']:
        c['address']['cc'] = known_country_code
    # Country code must be correct
    if not (len(c['address']['cc']) == 2 and c['address']['cc'] == c['address']['cc'].upper()):
        c['address']['cc'] = iso_countries.get_country_code(c['address']['cc'], default=known_country_code)
    else:
        c['address']['cc'] = iso_countries.clean_country_code(c['address']['cc'])
    info['contacts'][0] = c        
    return info


def registrant_create(epp_id, owner, **kwargs):
    """
    Creates new Registrant for given owner, but only if Registrant with same epp_id not exist yet.
    """
    if epp_id:
        existing_registrant = registrant_find(epp_id)
        if existing_registrant:
            if existing_registrant.owner.pk != owner.pk:
                raise Exception('Invalid owner, existing registrant have another owner already')
            logger.debug('registrant with epp_id=%s already exist', epp_id)
            return existing_registrant
    new_registrant = Registrant.registrants.create(epp_id=epp_id, owner=owner, **kwargs)
    logger.info('registrant created: %s', new_registrant)
    return new_registrant


def registrant_create_from_profile(owner, profile_object, epp_id=None):
    """
    Creates a new Registrant from existing Profile object. 
    """
    new_contact = Registrant.registrants.create(
        owner=owner,
        epp_id=epp_id,
        person_name=profile_object.person_name,
        organization_name=profile_object.organization_name or '',
        address_street=profile_object.address_street,
        address_city=profile_object.address_city,
        address_province=profile_object.address_province or '',
        address_postal_code=profile_object.address_postal_code or '',
        address_country=profile_object.address_country,
        contact_voice=profile_object.contact_voice or '',
        contact_fax=profile_object.contact_fax or '',
        contact_email=profile_object.contact_email,
    )
    logger.info('registrant created from existing profile: %s', new_contact)
    return new_contact


def registrant_update(epp_id, **kwargs):
    """
    Update given Registrant with new field values.
    """
    existing_registrant = registrant_find(epp_id)
    if not existing_registrant:
        raise Exception('Registrant not found')
    updated = Registrant.registrants.filter(pk=existing_registrant.pk).update(**kwargs)
    logger.info('registrant updated: %s', existing_registrant)
    return updated


def registrant_update_from_profile(registrant_object, profile_object, save=True):
    """
    Populate required fields for given `registrant_object` from existing Profile. 
    """
    registrant_object.person_name = profile_object.person_name
    registrant_object.organization_name = profile_object.organization_name or ''
    registrant_object.address_street = profile_object.address_street
    registrant_object.address_city = profile_object.address_city
    registrant_object.address_province = profile_object.address_province or ''
    registrant_object.address_postal_code = profile_object.address_postal_code or ''
    registrant_object.address_country = profile_object.address_country
    registrant_object.contact_voice = profile_object.contact_voice or ''
    registrant_object.contact_fax = profile_object.contact_fax or ''
    registrant_object.contact_email = profile_object.contact_email
    if save:
        registrant_object.save()
    return True


def registrant_find(epp_id):
    """
    If such Registrant exists with given epp_id - returns it, otherwise None.
    """
    return Registrant.registrants.filter(epp_id=epp_id).first()


def registrant_exists(epp_id):
    """
    Return `True` if Registrant with given epp_id exists, doing query in Registrant table.
    """
    return bool(Registrant.registrants.filter(epp_id=epp_id).first())


def get_registrant(owner):
    """
    Return Registrant object for given user or None, doing query in Registrant table.
    """
    return Registrant.registrants.filter(owner=owner).first()
