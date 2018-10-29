import logging

from back.models.contact import Contact

logger = logging.getLogger(__name__)


def exists(epp_id):
    """
    Return `True` if contact with given epp_id exists, doing query in Contact table.
    """
    return bool(Contact.contacts.filter(epp_id=epp_id).first())


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
