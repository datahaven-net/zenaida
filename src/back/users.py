from accounts.models import Account

from back.models.profile import Profile


def is_exist(email):
    """
    Return `True` if domain exists, doing query in Domain table.
    """
    return bool(Account.users.filter(email=email).first())


def find_account(email):
    """
    Return `Account` object created for that email address.
    """
    return Account.users.filter(email=email).first()


def create_account(email, account_password=None, also_profile=True, **kwargs):
    """
    Creates a new user account with given email and also new Profile object for him.
    All `kwargs` will be passed as field values to the new Profile object. 
    """
    new_account = Account.users.create_user(email, password=account_password)
    if also_profile:
        create_profile(new_account, **kwargs)
    return new_account


def create_profile(existing_account, **kwargs):
    """
    Creates new Profile for given Account.
    """
    return Profile.profiles.create(account=existing_account, **kwargs)
