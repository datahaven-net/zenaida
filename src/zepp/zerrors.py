
class EPPError(Exception):
    code = -1
    message = 'Unknown error'

    def __init__(self, message='', code=-1, response=None):
        self.code = code
        self.message = message
        if response:
            self.code = response['epp']['response']['result']['@code']
            if not self.message:
                self.message = response['epp']['response']['result']['msg']

    def __str__(self):
        return '[%s] %s' % (self.code, self.message)


class EPPConnectionFailed(EPPError):
    pass


class EPPResponseFailed(EPPError):
    pass


class EPPBadResponse(EPPError):
    pass


class EPPCommandFailed(EPPError):
    pass


class EPPCommandInvalid(EPPError):
    pass


class EPPUnexpectedResponse(EPPError):
    pass


class EPPRegistrarAuthFailed(EPPError):
    pass


class EPPRegistrantAuthFailed(EPPError):
    pass

