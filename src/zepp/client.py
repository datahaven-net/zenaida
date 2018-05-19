import os
import time
import json
import copy
import traceback
import random
import string
import pika
import uuid

#------------------------------------------------------------------------------

from zepp import xml2json

#------------------------------------------------------------------------------

_log_filename = "/home/zenaida/logs/zepp_client"
_error_log_filename = "/home/zenaida/logs/zepp_client.err"
_rabbitmq_client_credentials_filename = "/home/zenaida/keys/rabbitmq_gate_credentials.txt"

#------------------------------------------------------------------------------

LocaleInstalled = False

def _install_locale():
    """
    Here is a small trick to refresh current default encoding.
    """
    global LocaleInstalled
    if LocaleInstalled:
        return False
    try:
        import sys
        reload(sys)
        if hasattr(sys, "setdefaultencoding"):
            import locale
            denc = locale.getpreferredencoding()
            if denc != '':
                sys.setdefaultencoding(denc)
        LocaleInstalled = True
    except:
        pass
    return LocaleInstalled


def _enc(_s):
    _install_locale()
    s = '%s' % _s
    if type(s) != unicode:
        try:
            s = unicode(s)
        except:
            try:
                s = unicode(s, 'latin-1')
            except:
                try:
                    s = unicode(s, 'iso-8859-1')
                except:
                    try:
                        s = unicode(s, errors='replace')
                    except:
                        pass
                    pass
                pass
    return s


def _tr(_s):
    s = _enc(_s)
    try:
        # TODO:
        from transliterate import translit
        s = translit(s, reversed=True)
    except:
        pass
    return s

#------------------------------------------------------------------------------

class EPPResponseFailed(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return '[%s] %s' % (self.code, self.message)


class EPPBadResponse(Exception):
    pass


#------------------------------------------------------------------------------

class XML2JsonOptions(object):
    pretty = True

#------------------------------------------------------------------------------

def log_epp_errors(epp_errors=[]):
    global _error_log_filename
    if not epp_errors:
        epp_errors = [traceback.format_exc(), ]
    try:
        fout = open(_error_log_filename, 'a')
        for err in epp_errors:
            fout.write('\n%s\n%s\n' % (time.strftime('%m/%d %H:%M:%S'), err))
        fout.flush()
        os.fsync(fout)
        fout.close()
    except:
        try:
            fout.close()  # make sure file gets closed
        except:
            pass
    return


def epplog(txt):
    global _log_filename
    try:
        f = open(_log_filename, 'a')
        f.write(time.strftime('%m/%d %H:%M:%S') + ' ' + txt + '\n')
        f.flush()
        os.fsync(f.fileno())
        f.close()
    except:
        try:
            f.close()  # make sure file gets closed
        except:
            pass
    return

#------------------------------------------------------------------------------


class RPCClient:
    def __init__(self):
        global _rabbitmq_client_credentials_filename
        _host, _port, _username, _password = open(_rabbitmq_client_credentials_filename, 'r').read().strip().split(' ')
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=_host,
                port=int(_port),
                credentials=pika.credentials.PlainCredentials(
                    username=_username,
                    password=_password,
                ),
            )
        )
        self.connection.add_timeout(5, self.on_timeout)

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.reply_queue = result.method.queue

        self.channel.basic_consume(
            self.on_response,
            no_ack=True,
            queue=self.reply_queue
        )

    def on_timeout(self):
        self.connection.close()

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.reply = body

    def request(self, query):
        self.reply = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='epp_messages',
            properties=pika.BasicProperties(
                reply_to=self.reply_queue,
                correlation_id=self.corr_id,
            ),
            body=str(query)
        )
        while self.reply is None:
            self.connection.process_data_events()
        return self.reply

#------------------------------------------------------------------------------

def do_rpc_request(json_request):
    client = RPCClient()
    reply = client.request(json.dumps(json_request))
    return reply

#------------------------------------------------------------------------------

def run(json_request, raise_for_result=True, unserialize=True, logs=True):
    try:
        json_input = json.dumps(json_request)
    except Exception as exc:
        raise EPPBadResponse('wrong json input %s : %s' % (str(exc), json_request))

    if logs:
        epplog('>>> ' + json_input)

    try:
        out = do_rpc_request(json_request)
    except Exception as exc:
        epplog('!!! ' + traceback.format_exc())
        raise EPPBadResponse('epp request failed: %s' % str(exc))

    if not out:
        epplog('!!! EMPTY response from epp_gate, connection error')
        raise EPPBadResponse('epp request failed: empty response, connection error')

    json_output = None
    if unserialize:
        try:
            try:
                json_output = json.loads(xml2json.xml2json(out, XML2JsonOptions(), strip_ns=1, strip=1))
            except UnicodeEncodeError:
                json_output = json.loads(xml2json.xml2json(out.encode('ascii', errors='ignore'), XML2JsonOptions(), strip_ns=1, strip=1))
        except Exception as exc:
            raise EPPBadResponse('epp response unserialize failed: %s' % traceback.format_exc())
    if raise_for_result:
        if json_output:
            try:
                code = json_output['epp']['response']['result']['@code']
                msg = json_output['epp']['response']['result']['msg'].replace('Command failed;', '')
            except:
                if logs:
                    epplog('ERROR: ' + json_output)
                raise EPPBadResponse('wrong response, response code not found')
            if code not in ['1000', '1300', '1301', ]:
                if logs:
                    epplog('FAILED: ' + json.dumps(json_output, indent=2))
                raise EPPResponseFailed(code, msg)
        else:
            if out.count('Command completed successfully') == 0:
                if logs:
                    epplog('FAILED: ' + json.dumps(json_output, indent=2))
                raise EPPResponseFailed(-1, 'Command failed')
    if logs:
        epplog('<<< ' + json.dumps(json_output, indent=2) + '\n\n')
    return json_output or out

#------------------------------------------------------------------------------

def make_epp_id(email):
    rand4bytes = ''.join([random.choice(string.letters + string.digits) for _ in range(4)])
    return email.replace('.', '').split('@')[0][:6] + str(int(time.time() * 100.0))[6:] + rand4bytes.lower()

#------------------------------------------------------------------------------

def cmd_poll_req(**args):
    cmd = {
        'cmd': 'poll_req',
    }
    return run(cmd, logs=False, **args)

def cmd_poll_ack(msg_id, **args):
    cmd = {
        'cmd': 'poll_ack',
        'args': {
            'msg_id': msg_id,
        }
    }
    return run(cmd, logs=False, **args)

#------------------------------------------------------------------------------

def cmd_domain_check(domains, **args):
    return run({
        'cmd': 'domain_check',
        'args': {
            'domains': domains,
        },
    }, **args)

def cmd_domain_info(domain, auth_info=None, **args):
    cmd = {
        'cmd': 'domain_info',
        'args': {
            'name': domain,
        },
    }
    if auth_info is not None:
        cmd['args']['auth_info'] = auth_info
    return run(cmd, **args)

def cmd_domain_create(
        domain, nameservers, contacts_dict, registrant,
        auth_info=None, period='1', period_units='y', **args):
    """
    contacts_dict:
    {
        "admin": "abc123",
        "tech": "def456",
        "billing": "xyz999"
    }
    """
    cmd = {
        'cmd': 'domain_create',
        'args': {
            'name': domain,
            'nameservers': nameservers,
            'contacts': contacts_dict,
            'registrant': registrant,
            'period': period,
            'period_units': period_units,
        },
    }
    if auth_info is not None:
        cmd['args']['auth_info'] = auth_info
    return run(cmd, **args)

def cmd_domain_renew(domain, cur_exp_date, period, period_units='y', **args):
    cmd = {
        'cmd': 'domain_renew',
        'args': {
            'name': domain,
            'cur_exp_date': cur_exp_date,
            'period': period,
            'period_units': period_units,
        },
    }
    return run(cmd, **args)

def cmd_domain_update(domain,
                      add_nameservers_list=[], remove_nameservers_list=[],
                      add_contacts_list=[], remove_contacts_list=[],
                      change_registrant=None, auth_info=None, **args):
    """
    add_contacts_list and remove_contacts_list item:
    {
        "type": "admin",
        "id": "abc123",
    }
    """
    cmd = {
        'cmd': 'domain_update',
        'args': {
            'name': domain,
            'add_nameservers': add_nameservers_list,
            'remove_nameservers': remove_nameservers_list,
            'add_contacts': add_contacts_list,
            'remove_contacts': remove_contacts_list,
        }
    }
    if change_registrant is not None:
        cmd['args']['change_registrant'] = change_registrant
    if auth_info is not None:
        cmd['args']['auth_info'] = auth_info
    return run(cmd, **args)

def cmd_domain_transfer(domain, op, auth_info=None, period_years=None, **args):
    cmd = {
        'cmd': 'domain_transfer',
        'args': {
            'name': domain,
            'op': op,
        }
    }
    if auth_info is not None:
        cmd['args']['auth_info'] = auth_info
    if period_years is not None:
        cmd['args']['period_years'] = period_years
    return run(cmd, **args)

#------------------------------------------------------------------------------

def cmd_contact_check(contacts_ids, **args):
    return run({
        'cmd': 'contact_check',
        'args': {
            'contacts': contacts_ids,
        },
    }, **args)


def cmd_contact_info(contact_id, **args):
    return run({
        'cmd': 'contact_info',
        'args': {
            'contact': contact_id,
        },
    }, **args)


def cmd_contact_create(contact_id, email=None, voice=None, fax=None, auth_info=None, contacts_list=[], **args):
    """
    contacts_list item :
    {
        "name": "VeselinTest",
        "org":"whois",
        "address": {
            "street":["Street", "55"],
            "city": "City",
            "sp": "Nord Side",
            "cc": "AI",
            "pc": "1234AB"
        }
    }
    """
    cmd = {
        'cmd': 'contact_create',
        'args': {
            'id': contact_id,
            'contacts': [],
        },
    }
    if voice is not None:
        cmd['args']['voice'] = voice
    if fax is not None:
        cmd['args']['fax'] = fax
    if email is not None:
        cmd['args']['email'] = email
    if auth_info is not None:
        cmd['args']['auth_info'] = auth_info
    if email is not None:
        cmd['args']['email'] = email
    for cont in contacts_list[:]:
        international = copy.deepcopy(cont)
        international['type'] = 'int'
        if 'name' in international:
            international['name'] = '%s' % _tr(international['name'])
        if 'org' in international:
            international['org'] = '%s' % _tr(international['org'])
        if 'city' in international['address']:
            international['address']['city'] = '%s' % _tr(international['address']['city'])
        if 'sp' in international['address']:
            international['address']['sp'] = '%s' % _tr(international['address']['sp'])
        if 'pc' in international['address']:
            international['address']['pc'] = '%s' % _tr(international['address']['pc'])
        for i in range(len(international['address']['street'])):
            international['address']['street'][i] = '%s' % _tr(international['address']['street'][i])
        cmd['args']['contacts'].append(international)
    for cont in contacts_list[:]:
        loc = copy.deepcopy(cont)
        loc['type'] = 'loc'
        if 'name' in loc:
            loc['name'] = _enc(loc['name'])
        if 'org' in loc:
            loc['org'] = _enc(loc['org'])
        if 'city' in loc['address']:
            loc['address']['city'] = '%s' % _enc(loc['address']['city'])
        if 'sp' in loc['address']:
            loc['address']['sp'] = '%s' % _enc(loc['address']['sp'])
        if 'pc' in loc['address']:
            loc['address']['pc'] = '%s' % _enc(loc['address']['pc'])
        for i in range(len(loc['address']['street'])):
            loc['address']['street'][i] = '%s' % _enc(loc['address']['street'][i])
        cmd['args']['contacts'].append(loc)
    return run(cmd, **args)


def cmd_contact_update(contact_id, email=None, voice=None, fax=None, auth_info=None, contacts_list=[], **args):
    """
    contacts_list item :
    {
        "name": "VeselinTest",
        "org":"whois",
        "address": {
            "street":["Street", "55"],
            "city": "City",
            "sp": "Nord Side",
            "cc": "AI",
            "pc": "1234AB"
        }
    }
    """
    cmd = {
        'cmd': 'contact_update',
        'args': {
            'id': contact_id,
            'contacts': [],
        },
    }
    if voice is not None:
        cmd['args']['voice'] = voice
    if fax is not None:
        cmd['args']['fax'] = fax
    if email is not None:
        cmd['args']['email'] = email
    if auth_info is not None:
        cmd['args']['auth_info'] = auth_info
    for cont in contacts_list[:]:
        international = copy.deepcopy(cont)
        international['type'] = 'int'
        if 'name' in international:
            international['name'] = '%s' % _tr(international['name'])
        if 'org' in international:
            international['org'] = '%s' % _tr(international['org'])
        if 'city' in international['address']:
            international['address']['city'] = '%s' % _tr(international['address']['city'])
        if 'sp' in international['address']:
            international['address']['sp'] = '%s' % _tr(international['address']['sp'])
        if 'pc' in international['address']:
            international['address']['pc'] = '%s' % _tr(international['address']['pc'])
        for i in range(len(international['address']['street'])):
            international['address']['street'][i] = '%s' % _tr(international['address']['street'][i])
        cmd['args']['contacts'].append(international)
    for cont in contacts_list[:]:
        loc = copy.deepcopy(cont)
        loc['type'] = 'loc'
        if 'name' in loc:
            loc['name'] = _enc(loc['name'])
        if 'org' in loc:
            loc['org'] = _enc(loc['org'])
        if 'city' in loc['address']:
            loc['address']['city'] = '%s' % _enc(loc['address']['city'])
        if 'sp' in loc['address']:
            loc['address']['sp'] = '%s' % _enc(loc['address']['sp'])
        if 'pc' in loc['address']:
            loc['address']['pc'] = '%s' % _enc(loc['address']['pc'])
        for i in range(len(loc['address']['street'])):
            loc['address']['street'][i] = '%s' % _enc(loc['address']['street'][i])
        cmd['args']['contacts'].append(loc)
    return run(cmd, **args)

#------------------------------------------------------------------------------

def cmd_host_check(hosts_list, **args):
    return run({
        'cmd': 'host_check',
        'args': {
            'hosts': hosts_list,
        },
    }, **args)


def cmd_host_create(hostname, ip_address_list=[], **args):
    """
    ip_address_list item:
        {'ip': '10.0.0.1', 'version': 'v4' }
    """
    return run({
        'cmd': 'host_create',
        'args': {
            'name': hostname,
            'ip_address': ip_address_list,
        },
    }, **args)

#------------------------------------------------------------------------------
