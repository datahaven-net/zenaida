
class BillingError(Exception):
    message = 'Unknown error'

    def __init__(self, message='', *args, **kwargs):
        if message:
            self.message = message
        super(BillingError).__init__(*args, **kwargs)

    def __str__(self):
        return '%s' % (self.message, )


class DomainBlockedError(BillingError):

    message = 'Domain is blocked and can not be registered/renewed at the moment.'
