import logging

from back.models.contact import Contact
from zepp import iso_countries

logger = logging.getLogger(__name__)


def by_id(contact_id):
    """
    Return Contact object with given id.
    """
    return Contact.contacts.get(id=contact_id)


def exists(epp_id):
    """
    Return `True` if contact with given epp_id exists, doing query in Contact table.
    """
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


def create(epp_id, owner, **kwargs):
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
    new_contact = Contact.contacts.create(epp_id=epp_id, owner=owner, **kwargs)
    logger.debug('contact created: %s', new_contact)
    return new_contact


def update(epp_id, **kwargs):
    """
    Update given Contact with new field values.
    """
    existing_contact = Contact.contacts.filter(epp_id=epp_id).first()
    if not existing_contact:
        raise Exception('Contact not found')
    updated = Contact.contacts.filter(pk=existing_contact.pk).update(**kwargs)
    logger.debug('contact updated: %s', existing_contact)
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


def execute_contact_sync(contact_object):
    """
    """
    from automats import contact_synchronizer
    cs = contact_synchronizer.ContactSynchronizer(
        log_events=True,
        log_transitions=True,
        raise_errors=False,
    )
    cs.event('run', contact_object)
    outputs = list(cs.outputs)
    del cs
    if not outputs or not outputs[-1] or isinstance(outputs[-1], Exception):
        return False
    return True
