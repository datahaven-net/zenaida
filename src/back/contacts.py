from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from back.models.contact import Contact
from back.models.account import Account
from back.models.profile import Profile


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
    Creates new contact with given email.
    If corresponding Account not exist yet it will be created together with new Profile.
    """
    existing_profile = find_profile(email)
    if not existing_profile:
        new_account = Account.users.create_user(email, password=account_password)
        existing_profile = Profile(account=new_account, **kwargs)
        existing_profile.save()
    cont = Contact.contacts.create(epp_id=epp_id, profile=existing_profile)
    return cont


def update(email, **kwargs):
    """
    Update given Profile with new values if Account with given email exists.
    """
    try:
        updated = Profile.profiles.get(account_email=email).update(**kwargs)
    except (ObjectDoesNotExist, MultipleObjectsReturned, ):
        return False
    return updated


def find_profile(email):
    """
    Doing "email" lookup in Account table and returns related Profile object if found,
    else `None`.
    """
    try:
        accnt = Account.users.get(email=email)
    except (ObjectDoesNotExist, MultipleObjectsReturned, ):
        return None
    return accnt.profile
