import logging

#------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

class ZenaidaError(Exception):
    message = 'Unknown error'

    def __init__(self, message='', *args, **kwargs):
        if message:
            self.message = message
        super(ZenaidaEPPError).__init__(*args, **kwargs)

    def __str__(self):
        return '%s' % self.message

#------------------------------------------------------------------------------

class ZenaidaEPPError(ZenaidaError):
    code = -1
    message = 'Unknown EPP error'

    def __init__(self, message='', code=-1, response=None, *args, **kwargs):
        if response:
            self.code = response['epp']['response']['result']['@code']
            if not self.message:
                self.message = response['epp']['response']['result']['msg']
        if int(code) > 0:
            self.code = code
        if message:
            self.message = message
        super(ZenaidaEPPError).__init__(*args, **kwargs)

    def __str__(self):
        return '[%s] %s' % (self.code, self.message)

#------------------------------------------------------------------------------

class UnexpectedEPPResponse(ZenaidaError):
    pass


class CommandInvalid(ZenaidaError):
    pass


class DomainNotExist(ZenaidaError):
    pass


class NonSupportedZone(ZenaidaError):
    pass

#------------------------------------------------------------------------------

class RegistrarAuthFailed(ZenaidaEPPError):
    pass


class RegistrantAuthFailed(ZenaidaEPPError):
    pass


class RegistrantUnknown(ZenaidaEPPError):
    pass
