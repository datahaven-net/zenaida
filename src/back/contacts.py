
from back.models.contact import Contact
from back.models.profile import Profile

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
    if email and cont.profile.account.email != email:
        return False
    return True


def create(epp_id, email, account_password=None, **kwargs):
    """
    Creates new contact with given email, but only if Contact with same epp_id not exist yet.
    If corresponding Account not exist yet it will be created together with new Profile.
    """
    existing_contact = Contact.contacts.filter(epp_id=epp_id).first()
    if existing_contact:
        return existing_contact
    existing_account = users.find_account(email)
    if not existing_account:
        existing_account = users.create_account(email, account_password=account_password)
    new_contact = Contact.contacts.create(epp_id=epp_id, profile=existing_account.profile)
    return new_contact


def update(email, **kwargs):
    """
    Update given Profile with new values if Account with given email exists.
    """
    existing_account = users.find_account(email)
    if not existing_account:
        return False
    updated = Profile.profiles.filter(account=existing_account).update(**kwargs)
    return updated
