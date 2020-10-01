import logging

from accounts.models.account import Account

from back.models.profile import Profile

logger = logging.getLogger(__name__)


def is_exist(email):
    """
    Return `True` if domain exists, doing query in Domain table.
    """
    return bool(Account.users.filter(email=email.lower()).first())


def find_account(email):
    """
    Return `Account` object created for that email address.
    """
    return Account.users.filter(email=email.lower()).first()


def create_account(email, account_password=None, also_profile=True, is_active=False, **kwargs):
    """
    Creates a new user account with given email and also new Profile object for him.
    All `kwargs` will be passed as field values to the new Profile object. 
    """
    new_account = Account.users.create_user(
        email=email.lower(),
        password=account_password,
        is_active=is_active,
    )
    if also_profile:
        create_profile(new_account, **kwargs)
    logger.info('account created: %r', new_account)
    return new_account


def create_profile(existing_account, **kwargs):
    """
    Creates new Profile for given Account.
    """
    prof = Profile.profiles.create(account=existing_account, **kwargs)
    logger.info('profile created: %r', prof)
    return prof


def erase_profile_details(existing_account):
    """
    Erase all profile fields for given user and make it invalid. 
    """
    prof = existing_account.profile
    prof.person_name = ''
    prof.organization_name = ''
    prof.address_street = ''
    prof.address_city = ''
    prof.address_province = ''
    prof.address_postal_code = ''
    prof.address_country = ''
    prof.contact_voice = ''
    prof.contact_fax = ''
    prof.contact_email = ''
    prof.save()
    return True


def generate_password(length):
    """
    Call Django `make_random_password()` method.
    """
    return Account.users.make_random_password(length=length)
