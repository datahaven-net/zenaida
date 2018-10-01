from back.models.contact import Contact

from back import users


def exists(epp_id):
    """
    Return `True` if contact with given epp_id exists, doing query in Contact table.
    """
    return bool(Contact.contacts.filter(epp_id=epp_id).first())


def verify(epp_id, email):
    """
    Make sure that existing contact with given epp_id have same info.
    """
    if not exists(epp_id):
        return False
    cont = Contact.contacts.get(epp_id=epp_id)
    if email and cont.owner.email != email:
        return False
    return True


def create(email, epp_id=None, account_password=None, **kwargs):
    """
    Creates new contact with given email, but only if Contact with same epp_id not exist yet.
    If corresponding Account not exist yet it will be created together with new Profile.
    Value `account_password` will be passed to `users.create_account()` method if new user to be created.
    """
    if epp_id:
        existing_contact = Contact.contacts.filter(epp_id=epp_id).first()
        if existing_contact:
            return existing_contact
    existing_account = users.find_account(email)
    if not existing_account:
        existing_account = users.create_account(email, account_password=account_password)
    new_contact = Contact.contacts.create(epp_id=epp_id, owner=existing_account)
    return new_contact


def update(email=None, epp_id=None, **kwargs):
    """
    Update given Contact with new field values.
    """
    existing_epp_contact = None
    if epp_id:
        existing_epp_contact = Contact.contacts.filter(epp_id=epp_id).first()
    existing_contacts = []
    if email:
        if existing_epp_contact:
            if existing_epp_contact.owner.email != email:
                raise Exception('Invalid email, existing contact have another owner already')
            existing_contacts.append(existing_epp_contact)
        else:
            existing_contacts = Contact.contacts.filter(owner__email=email).all()
    if not existing_contacts:
        raise Exception('Contact not found')
    if len(existing_contacts) > 1:
        raise Exception('Multiple contacts found')
    target_contact = existing_contacts[0]
    updated = Contact.contacts.filter(pk=target_contact.pk).update(**kwargs)
    return updated
