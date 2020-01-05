from accounts.models import Account


def list_all_users_by_date(year, month=None):
    if year and month:
        return Account.users.filter(date_joined__year=year, date_joined__month=month)
    else:
        return Account.users.filter(date_joined__year=year)
