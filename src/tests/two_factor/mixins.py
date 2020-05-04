from zen import zusers


class UserMixin(object):
    def setUp(self):
        super().setUp()
        self._passwords = {}

    def create_user(self, email='test@example.com', password='secret', **kwargs):
        user = zusers.create_account(email=email, account_password=password, is_active=True)
        self._passwords[user] = password
        return user

    def enable_otp(self, user=None):
        if not user:
            user = list(self._passwords.keys())[0]
        return user.totpdevice_set.create(name='default')
