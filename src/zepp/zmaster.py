
from pika.exceptions import AMQPError
from zepp import client
from zepp import exceptions


def domain_check(domain, raise_errors=False, return_string=False, return_response=False, ):
    """
    Return True (domain exist), False (domain not exist), None (if error) or string (with error message).
    If return_response==True always return EPP response as dictionary.
    If raise_errors==True always raise exceptions in case of errors.
    If return_string==True always return error message as string in case of errors.
    """
    try:
        check = client.cmd_domain_check([domain, ], )
    except AMQPError as exc:
        if raise_errors:
            raise exceptions.EPPCommandFailed(str(exc))
        if return_string:
            return 'domain check request failed, connection broken: %s' % exc
        return None
    except Exception as exc:
        if raise_errors:
            raise exceptions.EPPCommandFailed(str(exc))
        if return_string:
            return 'domain check request failed, unknown error: %s' % exc
        return None
    if check['epp']['response']['result']['@code'] != '1000':
        if raise_errors:
            raise exceptions.EPPCommandFailed('EPP domain_check failed with error code: %s' % (
                check['epp']['response']['result']['@code'], ))
        if return_response:
            return check
        if return_string:
            return 'domain check request failed with error code: %s' % check['epp']['response']['result']['@code']
        return None
    if not check['epp']['response']['resData']['chkData']['cd']['reason'].startswith('(00)'):
        if raise_errors:
            raise exceptions.EPPCommandFailed('EPP domain_check failed with reason: %s' % (
                check['epp']['response']['resData']['chkData']['cd']['reason']))
        if return_response:
            return check
        if return_string:
            return 'domain check request failed with reason: %s' % check['epp']['response']['resData']['chkData']['cd']['reason']
        return None
    if check['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '1':
        if return_response:
            return check
        if return_string:
            return 'not exist'
        return False
    if return_response:
        return check
    if return_string:
        return 'exist'
    return True


def domain_register(domain):
    """
    """
