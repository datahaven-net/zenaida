#!/usr/bin/python

import os
import sys
import string
import hmac
import tempfile
import random
import urllib
import smtplib
import json
import re
import datetime
import time

from email import Encoders
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate, parsedate

#------------------------------------------------------------------------------

sys.path.append('/home/veselin/datahaven/whois/conf')
sys.path.append('/home/whois.ai/conf')

sys.path.append('/home/veselin/datahaven/whois/cgi-bin')
sys.path.append('/home/whois.ai/cgi-bin')

sys.path.append('/home/veselin/datahaven/whois/')
sys.path.append('/home/whois.ai/')

sys.path.append('/Users/veselin/work/datahaven/whois/')
sys.path.append('/Users/veselin/work/datahaven/whois/conf/')

#------------------------------------------------------------------------------

from whois_conf import (
    TESTING,
    VERIFY_GOD_IP,
    god_ip_list_file,
    sessions_dir_path,
    users_info_dir,
    index_domains_dir,
    whois_path,
    domains_index_path,
    domains_god_index_path,
    users_path,
    session_prefix,
    balance_transactions_dir_path,
    login_log_file_path,
    protection_log_file_path,
    maintanance_mode_users_list_file,
    ip_filter_dir,
    hmac_key_word,
    send_email_conf_raw,
    send_sms_conf_raw,
)

from whois_constants import (
    sms_status_message,
    no_email_str,
)

#------------------------------------------------------------------------------

tempfile.tempdir = sessions_dir_path()
sys.stderr = sys.stdout

#------------------------------------------------------------------------------

def cgi_escape(inp):
    try:
        sys.path.remove('')
        sys.path.append('')
    except:
        pass
    out = inp
    try:
        from cgi import escape
        out = escape(inp)
    except:
        pass
    return out


def god_ip():
    if not VERIFY_GOD_IP():
        return True
    if not os.path.isfile(god_ip_list_file()):
        return True
    fin = open(god_ip_list_file(), 'r')
    src = fin.read()
    fin.close()
    iplist = src.split('\n')
    current_ip = ''
    try:
        current_ip = cgi_escape(os.environ.get('REMOTE_ADDR', '0.0.0.0')).strip()
    except:
        return False

    for ip in iplist:
        if ip.strip() == '':
            continue
        if current_ip == ip.strip():
            return True
    return False

#------------------------------------------------------------------------------
#--- EMAIL, FAX, LETTER, SMS
#------------------------------------------------------------------------------

def check_correct_email(email, full_check=False):
    regexp = '^[\w\-\.\@]*$'
    if re.match(regexp, email) is None:
        return False
    if email.startswith('.'):
        return False
    if email.endswith('.'):
        return False
    if email.startswith('-'):
        return False
    if email.endswith('-'):
        return False
    if email.startswith('@'):
        return False
    if email.endswith('@'):
        return False
    if len(email) < 3:
        return False
    if len(email) > 250:
        return False
    if full_check:
        if email.count('@') != 1:
            return False
        regexp2 = '^[\w\-\.]*\@[\w\-\.]*$'
        if re.match(regexp2, email) is None:
            return False
    return True


def check_correct_phone(value):
    regexp = '^[ \d\-\+]*$'
    if re.match(regexp, value) is None:
        return False
    if len(value) < 5:
        return False

    return True


def check_correct_address(value):
    regexp = '^[ \r\n\w\-\.\#\,\:\;\'\"\/\~\`\+\(\)]*$'
    if re.match(regexp, value) is None:
        return False
    if len(value) < 5:
        return False

    return True


def SendEmail(TO, FROM, HOST, PORT, LOGIN, PASSWORD, SUBJECT, BODY, FILES):
    msg = MIMEMultipart()
    msg["From"] = FROM
    msg["To"] = TO
    msg["Subject"] = SUBJECT
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(BODY))

    # attach a file
    for filePath in FILES:
        if not os.path.isfile(filePath):
            continue
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(filePath, "rb").read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(filePath))
        msg.attach(part)

    s = smtplib.SMTP(HOST, PORT)
    #s.set_debuglevel(True) # It's nice to see what's going on
    s.ehlo()  # identify ourselves, prompting server for supported features
    if s.has_extn('STARTTLS'):
        s.starttls()
        s.ehlo()  # re-identify ourse
    s.login(LOGIN, PASSWORD)  # optional
    errors = s.sendmail(FROM, TO, msg.as_string())
    s.close()
    return errors


def send_email(to_address, subject, message):
    try:
        send_email_info = json.loads(send_email_conf_raw())
    except:
        send_email_info = {
            'from_address': 'ai.hostmaster@gmail.com',
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_login': 'ai.hostmaster@gmail.com',
            'smtp_password': 'password',
        }
    try:
        SendEmail(
            to_address,
            send_email_info['from_address'],
            send_email_info['smtp_host'],
            send_email_info['smtp_port'],
            send_email_info['smtp_login'],
            send_email_info['smtp_password'],
            subject,
            message,
            [],
        )
    except:
        pass


def sendPassword(email, password):
    message = '''
Hello.

You request for registration in the AI domains.

Your password to sign in the AI domains : %s

Thank you for registration!
http://whois.ai
    ''' % password
    send_email(email, 'AI Registry Password.', message)


def testEmail(email):
    message = '''
Hello.

This email was sent from whois.ai to test that we can send you email
and that is is not lost in your spam filter.

Thank you.
http://whois.ai
    '''
    send_email(email, 'AI Registry Verification.', message)


def sendVerificationCode(email, vcode):
    message = '''
Hello,

You have signed up to register AI domain names.
This e-mail is to confirm your mail address.  Please login
with your email address and password and enter
your Mail Verification Code of: %s

Thanks,
http://whois.ai
''' % vcode
    send_email(email, 'AI Registry .', message)


def sendTrustNotification(email):
    message = '''
Hello.

Your account on http://whois.ai is now active and you can start registering domains under ".ai".
Note that the fee so far was just for the account and did not include any domains.
See http://whois.ai/faq.html for more information.

Thanks,
http://whois.ai
'''
    send_email(email, 'AI Registry .', message)


def sendDomainDeleteNotification(email, domain):
    message = '''
Hello.

Your domain "%s" on http://whois.ai being deleted.
See http://whois.ai/faq.html for more information.

Thanks,
http://whois.ai
''' % domain
    send_email(email, 'AI Registry .', message)


def sendDomainTransferredNotification(email, domain):
    message = '''
Hello.

Your domain "%s" was successfully transferred to another registrar.

Thanks,
http://whois.ai
''' % domain
    send_email(email, 'AI Registry .', message)


def sendFax(number, email, vcode):
    number_ = number.replace(' ', '')
    dst_email = str(number_) + '@efaxsend.com'
    message = '''
Hello,

You have signed up to register AI domain names.
This fax is to confirm your mail address.  Please login
with your registered email address (%s) and enter
your Mail Verification Code of: %s

Thanks,
http://whois.ai
    ''' % (email, vcode)
    send_email(dst_email, 'AI Registry .', message)


def sendLetter(address, email, vcode):
    message = '''
Hello,

You have signed up to register AI domain names.
This letter is to confirm your mail address.  Please login
with your registered email address (%s) and enter
your Mail Verification Code of: %s

Thanks,
http://whois.ai
    ''' % (email, vcode)

    dst_email = 'quickletter@postful.com'
    subject = address.replace('\n', ', ')
    send_email(dst_email, subject, message)


def sendSMS(number=None, vcode=None, sms_text=None):
    try:
        send_sms_info = json.loads(send_sms_conf_raw())
    except:
        send_sms_info = {
            "sms_username": "user",
            "sms_password": "passwd",
            "sms_api_id": "1234567",
            "sms_alert_number": "01234567",
        }
    if not number:
        number = send_sms_info['sms_alert_number']
    if not sms_text:
        sms_text = "Hello. You have signed up to register AI domain names. Your SMS Verification Code is: %s" % vcode
    sms_text = sms_text.replace(' ', '+')
    sms_to = str(number)
    if sms_to.startswith('+'):
        sms_to = sms_to[1:]
    url = "https://api.clickatell.com/http/sendmsg?api_id=%s&user=%s&password=%s&to=%s&text=%s" % (
        send_sms_info['sms_api_id'],
        send_sms_info['sms_username'],
        send_sms_info['sms_password'],
        sms_to,
        sms_text,
    )
    f = urllib.urlopen(url)
    r = f.read()
    if r.startswith('ID:'):
        try:
            return (True, r.split(' ')[1].strip())
        except:
            return (False, '')
    elif r.startswith('ERR:'):
        return (False, r)
    else:
        return (False, 'Wrong gateway response. Pleace contact hostmaster.')


def getSMSstatus(sms_id):
    try:
        send_sms_info = json.loads(send_sms_conf_raw())
    except:
        send_sms_info = {
            "sms_username": "user",
            "sms_password": "passwd",
            "sms_api_id": "1234567"
        }
    url = "https://api.clickatell.com/http/querymsg?api_id=%s&user=%s&password=%s&apimsgid=%s" % (
        send_sms_info['sms_api_id'],
        send_sms_info['sms_username'],
        send_sms_info['sms_password'],
        sms_id,
    )
    f = urllib.urlopen(url)
    r = f.read()
    if r.startswith('ID:'):
        try:
            return (True, sms_status_message(r.split(' ')[3].strip()))
        except:
            return (False, '')
    elif r.startswith('ERR:'):
        return (False, r)
    else:
        return (False, 'Wrong gateway response. Pleace contact hostmaster.')


#-------------------------------------------------------------------------------
#--- USERS INFO
#-------------------------------------------------------------------------------

def find_user_info(login):
    user_file_path = users_info_dir() + login
    if not os.path.exists(user_file_path):
        return ''
    fin = open(user_file_path, 'r')
    userinfo = fin.read()
    fin.close()
    return userinfo


def write_user_info(login, info, users_info_dir_path=None):
    if not users_info_dir_path:
        users_info_dir_path = users_info_dir()
    user_file_path = os.path.join(users_info_dir_path, login)
    fout = open(user_file_path, 'w')
    fout.write(info)
    fout.close()
    if TESTING():
        try:
            os.chmod(user_file_path, 0666)
        except:
            pass


def make_raw_info(data, new_info=False):
    info = ''
    if new_info:
        data['datetime'] = formatdate()
        data['verif_fax'] = formatdate()
        data['verif_mail'] = formatdate()
        data['ip'] = cgi_escape(os.environ.get('REMOTE_ADDR', '0.0.0.0'))
    keys = data.keys()
    keys.sort()
    for key in keys:
        value = data[key].replace('\r\n', ',')
        value = value.replace('\n', ',')
        try:
            value = str(value)
        except:
            try:
                value = str(unicode(value, errors='replace'))
            except:
                value = '?'
        info += key + ' ' + value + '\n'
    return info


def split_raw_info(info, data):
    lines = info.split('\n')
    for line in lines:
        words = line.split(' ')
        key = words[0]
        value = ''
        if len(words) > 1:
            value = line[len(key) + 1:]
        if key.strip() != '':
            data[key] = value
    return True


def read_info(email, data):
    """
    read personal information for given user
    """
    userinfo = find_user_info(email)
    if userinfo == '':
        return False
    return split_raw_info(userinfo, data)


def save_info(email, data, new_info=False, users_info_dir_path=None):
    """
    write personal information to file
    """
    userinfo = make_raw_info(data, new_info)
    write_user_info(email, userinfo, users_info_dir_path=users_info_dir_path)


def get_single_info(email, key, default=''):
    user = email.lower().strip()
    if not check_correct_email(user):
        return default
    udict = {}
    if not read_info(user, udict):
        return default
    if key not in udict:
        return default
    return udict[key]


def write_single_info(email, key, value):
    user = email.lower().strip()
    if not check_correct_email(user):
        return False
    udict = {}
    if not read_info(user, udict):
        return False
    udict[key] = value
    write_user_info(email, udict)
    return True


def findUser(user, passw):
    user = user.lower().strip()
    if not check_correct_email(user):
        return 'email'
    passw = passw.strip()
    uinfo = find_user_info(user)
    if uinfo == '':
        return 'login'
    udict = {}
    split_raw_info(uinfo, udict)
    if 'password' not in udict:
        return 'nopassw'
    if udict['password'] != passw:
        return 'password'
    return ''


def scanForEmailShell(email, whoisdir=whois_path()):
    """
    scan all forms which belongs to given e-mail and return list of forms paths
    use shell commands "find" and "grep" to filter out needed domains
    """
    try:
        import shlex
        import subprocess
        cmd = "find %s -type f -exec grep -l -H '%s' {} +" % (whoisdir, email)
        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
        output = proc.communicate()[0]
        return output.splitlines()
    except:
        return []


def checkExistingUser(user):
    """
    just check for user acount
    """
    user = user.lower().strip()
    if not check_correct_email(user):
        return False
    uinfo = find_user_info(user)
    if uinfo == '':
        return False
    return True


def createUser(email, password):
    """
    creates new user acount
    """
    user = email.lower().strip()
    if not check_correct_email(user):
        return
    udict = {}
    udict['email'] = user
    udict['password'] = password
    save_info(user, udict, new_info=True)


def generatePassword(length=12, strong=True):
    """
    generates a new random password
    """
    random.seed()
    if not strong:
        return ''.join([random.choice(string.letters + string.digits) for _ in range(length)])
    lower_length = int(length / 3)
    upper_length = int(length / 3)
    digits_lendth = length - upper_length - lower_length
    lower_pwd = [random.choice(string.lowercase) for _ in range(lower_length)]
    upper_pwd = [random.choice(string.uppercase) for _ in range(upper_length)]
    digits_pwd = [random.choice(string.digits) for _ in range(digits_lendth)]
    pwd = lower_pwd + upper_pwd + digits_pwd
    random.shuffle(pwd)
    return ''.join(pwd)


def getPassword(user):
    """
    return password for user acount
    """
    return get_single_info(user, 'password')


def updateUser(user):
    """
    if user does not exist creates it with random password
    """
    user = user.lower().strip()
    if not check_correct_email(user):
        return
    passw = getPassword(user.strip().lower())
    if passw == '':
        createUser(user.strip().lower(), generatePassword())

#------------------------------------------------------------------------------
#--- LIST DOMAINS and INDEXING
#------------------------------------------------------------------------------

def is_user_domains_indexed(email):
    path = index_domains_dir() + email
    return os.path.exists(path)


def is_user_domains_index_valid(email):
    path = index_domains_dir() + email
    if not os.path.exists(path):
        return False
    try:
        tm = os.path.getmtime(path)
    except:
        return False
    return time.time() - tm < 7 * 24 * 60 * 60


def read_user_domains_records(email):
    path = index_domains_dir() + email
    if not os.path.exists(path):
        return []
    try:
        fin = open(path, 'r')
        src = fin.read()
        fin.close()
    except:
        return []
    return src.splitlines()


def read_user_domains(email):
    return [d.split('|')[0] for d in read_user_domains_records(email)]


def read_user_domains_paths(email):
    from domains import domainPath
    return [domainPath(d) for d in read_user_domains(email)]


def write_user_domains(email, domains_list):
    if not os.path.isdir(index_domains_dir()):
        try:
            os.makedirs(index_domains_dir())
        except:
            pass
    try:
        path = index_domains_dir() + email
        fout = open(path, 'w')
        fout.write('\n'.join(sorted(domains_list)))
        fout.close()
    except:
        if TESTING():
            import traceback
            traceback.print_exc()
        return False
    if TESTING():
        try:
            os.chmod(path, 0666)
        except:
            pass
    return True


def addUserDomain(email, domain, expire=''):
    """
    remember that domain for given user
    """
    email = email.lower().strip()
    if not email or email == no_email_str:
        return False
    new_record = '%s|%s' % (domain, expire)
    cur_domains = read_user_domains_records(email)
    new_domains = []
    found = False
    for record in cur_domains:
        if record.startswith(domain):
            found = True
            new_domains.append(new_record)
            continue
        new_domains.append(record)
    if not found:
        new_domains.append(new_record)
    write_user_domains(email, new_domains)
    return True


def removeUserDomain(email, domain):
    """
    erase given domain from index file for given user
    """
    email = email.lower().strip()
    if email == no_email_str:
        return False
    cur_domains = read_user_domains_records(email)
    new_domains = []
    found = False
    for record in cur_domains:
        if record.startswith(domain):
            found = True
            continue
        new_domains.append(record)
    write_user_domains(email, new_domains)
    return found


def invalidateIndexedDomains(domains):
    if not os.path.isdir(index_domains_dir()):
        return 0
    removed = 0
    for email in os.listdir(index_domains_dir()):
        cur_domains = read_user_domains(email)
        for domain in domains:
            if domain in cur_domains:
                removed += 1
                removeUserDomain(email, domain)
    return removed


def getUserDomainsList(email):
    """
    get domains for this user from his info
    """
    return filter(None, get_single_info(email, 'domains', '').split(','))


def setUserPassword(user_, password):
    """
    set new password for user
    """
    user = user_.lower().strip()
    if not check_correct_email(user):
        return
    udict = {}
    if not read_info(user, udict):
        return
    udict['password'] = password.strip()
    save_info(user, udict)


def filter_user_domains_from_index(email):
    from domains import domainPath, readform
    if not email or email == no_email_str:
        return []
    domains_list_from_info = read_user_domains(email)
    filtered_domains = []
    for domain_name in domains_list_from_info:
        domain = domainPath(domain_name)
        if os.access(domain, os.F_OK) == 0:
            continue
        form = {}
        fin = open(domain, 'r')
        readform(form, fin)
        fin.close()
        ok = False
        if form['4l.'] != '' and form['4l.'].strip().lower() == email.lower():
            ok = True
        if form['5l.'] != '' and form['5l.'].strip().lower() == email.lower():
            ok = True
        if form['6l.'] != '' and form['6l.'].strip().lower() == email.lower():
            ok = True
        if ok:
            filtered_domains.append(domain)
    return filtered_domains


def build_index_for_user(email, whoisdir=whois_path()):
    from domains import readform, log_input
    dt = time.time()
    user_domains = []
    deduplicated = set()
    for domain_path in scanForEmailShell(email, whoisdir):
        form = {}
        fin = open(domain_path, 'r')
        readform(form, fin)
        fin.close()
        domain_emails = []
        for x in ['4l.', '5l.', '6l.']:
            _email = form[x].strip().lower()
            if _email:
                domain_emails.append(_email)
        if email not in domain_emails:
            continue
        domain = form['2.'].lower()
        expire = form['1b.']
        record = '%s|%s' % (domain, expire)
        if domain not in deduplicated:
            deduplicated.add(domain)
            user_domains.append(record)
    write_user_domains(email, user_domains)
    dt = time.time() - dt
    log_input('users.py', dict(msg='domain index for %s was updated within %s seconds' % (email, dt)))
    return user_domains


def create_domains_index_file(inpath=whois_path(), outpath=domains_index_path(), logs=False):
    """
    index all domains and fill domains for each user
    """
    from domains import domainPathList, readform
    users = {}
    total_domains = 0
    for domain_path in domainPathList(inpath):
        dform = {}
        fin = open(domain_path, 'r')
        readform(dform, fin)
        fin.close()
        domain = dform.get('2.', '').lower()
        expire = dform.get('1b.', '')
        if domain == '':
            continue
        total_domains += 1
        record = '%s|%s' % (domain, expire)
        for email in [dform[x].lower().strip() for x in ['4l.', '5l.', '6l.']]:
            if not email.strip():
                continue
            if email not in users:
                users[email] = []
            duplicated = False
            for cur_record in users[email]:
                if cur_record.startswith(domain):
                    duplicated = True
            if not duplicated:
                users[email].append(record)
        if logs:
            print 'read success:', domain_path
    fout = open(outpath + '.tmp', 'w')
    usrkeys = users.keys()
    usrkeys.sort()
    for user in usrkeys:
        fout.write(user.lower() + ':' + (';'.join(users[user])) + '\n')
    os.fsync(fout)
    fout.close()
    os.rename(outpath + '.tmp', outpath)
    if logs:
        print "file %s created" % outpath


def update_domains_index_from_file(inpath=domains_index_path(), logs=False):
    """
    generate all index files for all users from existing domains index file
    """
    fin = open(inpath, 'r')
    usersdata = fin.read()
    fin.close()
    usersdata = usersdata.split("\n")
    total_domains = 0
    total_users = 0
    for usr in usersdata:
        if usr.strip() == '':
            continue
        total_users += 1
        email, user_domains = usr.split(':', 1)
        user_domains = user_domains.split(';')
        total_domains += len(user_domains)
        write_user_domains(email, user_domains)
        if logs:
            print 'wrote success:', email
    if logs:
        print 'total domains indexed:', total_domains
        print 'total emails indexed:', total_users


def index_all_domains(inpath=whois_path(), logs=False):
    """
    index all domains and fill domains for each user
    """
    from domains import domainPathList, readform
    all_domains = {}
    for domain_path in domainPathList(inpath):
        dform = {}
        fin = open(domain_path, 'r')
        readform(dform, fin)
        fin.close()
        domain = dform.get('2.', '').lower()
        if domain == '':
            continue
        if domain not in all_domains:
            all_domains[domain] = {}
        all_domains[domain]['paid'] = dform.get('1a.', '')
        all_domains[domain]['expire'] = dform.get('1b.', '')
        all_domains[domain]['emails'] = {}
        for x in ['4l.', '5l.', '6l.']:
            email = dform[x].lower().strip()
            if not email.strip():
                continue
            all_domains[domain]['emails'][x] = email
        if logs:
            print 'read success:', domain_path
    write_all_indexed_domains(all_domains, logs)


def write_all_indexed_domains(all_domains, logs=False):
    fout = open(domains_god_index_path(), 'w')
    domainskeys = all_domains.keys()
    domainskeys.sort()
    for domain in domainskeys:
        if logs:
            print 'writing:', domain
        fout.write(domain.lower() + '\n')
        fout.write(json.dumps(all_domains[domain]) + '\n')
    os.fsync(fout)
    fout.close()
    if logs:
        print 'total domains indexed:', len(all_domains)


def read_all_indexed_domains():
    all_domains = {}
    fin = open(domains_god_index_path(), 'r')
    while True:
        domain = str(fin.readline().strip())
        if not domain:
            break
        try:
            data = json.loads(fin.readline())
        except:
            continue
        all_domains[domain] = data
    fin.close()
    return all_domains


def remove_domains_from_index(domains_names, logs=False):
    all_domains = read_all_indexed_domains()
    removed = 0
    for domain in domains_names:
        if domain not in all_domains.keys():
            if logs:
                print 'domain %s was not found in the index, can`t remove' % domain
            continue
        all_domains.pop(domain)
        removed += 1
    if logs:
        print "total domains removed: %d" % removed
    write_all_indexed_domains(all_domains, logs)

#------------------------------------------------------------------------------
#--- ACCOUNTS and PASSWORDS
#------------------------------------------------------------------------------

def getUserDateTime(user):
    """
    get datetime value of user registration
    """
    return get_single_info(user, 'datetime')


def generate_users_file(inpath, print_logs=False):
    """
    generate users file from domain forms
    """
    from domains import domainPathList, readform
    users = {}
    for domain_path in domainPathList(inpath):
        if print_logs:
            print domain_path
        dform = {}
        fin = open(domain_path, 'r')
        readform(dform, fin)
        fin.close()
        if dform['4l.'] != '':
            users[dform['4l.']] = generatePassword()
        if dform['5l.'] != '':
            users[dform['5l.']] = generatePassword()
        if dform['6l.'] != '':
            users[dform['6l.']] = generatePassword()
    fout = open(users_path() + '.tmp', 'w')
    usrkeys = users.keys()
    usrkeys.sort()
    for user in usrkeys:
        fout.write(user.lower() + ':' + users[user] + '\n')
    os.fsync(fout)
    fout.close()
    os.rename(users_path() + '.tmp', users_path())
    if print_logs:
        print 'file %s was generated' % users_path()


def generate_all_profiles(paid=False, users_info_dir_path=None, print_logs=False):
    """
    generate all users info files from users file
    """
    fin = open(users_path(), 'r')
    usersdata = fin.read()
    fin.close()
    users = usersdata.split("\n")
    for usr in users:
        if usr.strip() == '':
            continue
        usr_prms = usr.split(':')
        udict = {}
        udict['email'] = usr_prms[0]
        udict['password'] = usr_prms[1]
        udict['pay100date'] = formatdate()
        udict['verif_fax'] = formatdate()
        udict['verif_phone'] = formatdate()
        udict['verif_mail'] = formatdate()
        if paid:
            udict['pay100date'] = formatdate()
            udict['fax_code'] = generatePassword(10)
            udict['mail_code'] = generatePassword(10)
            udict['sms_code'] = generatePassword(10)
        save_info(udict['email'], udict, new_info=True, users_info_dir_path=users_info_dir_path)
        if print_logs:
            print udict
            print


def add_to_all_profiles(key, value):
    for email in os.listdir(users_info_dir()):
        email_path = users_info_dir() + email
        if os.path.isfile(email_path) == 0:
            continue
        uinfo = {}
        if not read_info(email, uinfo):
            continue
        uinfo[key] = value
        try:
            save_info(email, uinfo)
        except:
            pass


def regenerate_passwords():
    """
    regenerate passwords for all users profiles
    """
    for email in os.listdir(users_info_dir()):
        email_path = users_info_dir() + email
        if os.path.isfile(email_path) == 0:
            continue
        uinfo = {}
        if not read_info(email, uinfo):
            continue
        uinfo['password'] = generatePassword()
        save_info(email, uinfo)

#-------------------------------------------------------------------------------
#--- COOKIES
#-------------------------------------------------------------------------------

#check user authorization
def testCookie(cookie):
    if 'login' not in cookie:
        return False
    if 'password' not in cookie:
        return False

    cook_login = cookie['login'].value
    cook_password = cookie['password'].value

    if not check_correct_email(cook_login):
        return False

    if cook_login == no_email_str:
        return False

    usr_password = getPassword(cook_login)
    if usr_password == '':
        return False
    h = hmac.HMAC(hmac_key_word(), time.strftime('%Y%m%d') + usr_password + cook_login)
    if h.hexdigest().upper() != cook_password:
        return False

    return True


def killCookie(cookie):
    """
    kill cookie in current session
    """
    try:
        login = cookie['login']
    except:
        login = ''
    os.environ['HTTP_COOKIE'] = ''
    cookie['login'] = ''
    cookie['password'] = ''
    cookie['session'] = ''
    print cookie
    open(protection_log_file_path(), 'a').write('cookie killed for user: %s' % login)

#-------------------------------------------------------------------------------
#--- TRANSACTIONS
#-------------------------------------------------------------------------------

def testExistingTransaction(tranid):
    return os.path.isfile(os.path.join(sessions_dir_path(), tranid))


def getTransactionDelay(login):
    uinfo = {}
    read_info(login, uinfo)
    timestr = uinfo.get('last_transaction_time', '')
    if timestr == '':
        timestr = formatdate(time.time(), True)
        uinfo['last_transaction_time'] = timestr
        save_info(login, uinfo)
    dtm = parsedate(timestr)
    if dtm is None:
        return 0
    return float(time.time() - time.mktime(dtm))


def setTransactionDelay(login):
    uinfo = {}
    read_info(login, uinfo)
    uinfo['last_transaction_time'] = formatdate(time.time(), True)
    save_info(login, uinfo)


def addTransaction(info_string, email='', trans_date=formatdate()):
    """
    creates new transaction
    """
    prefixI = time.strftime(session_prefix())
    invoice_file_num, invoice_path = tempfile.mkstemp("", prefixI, sessions_dir_path())
    fout = os.fdopen(invoice_file_num, "w")
    fout.write(email + '>>>' + trans_date + '>>>' + info_string)
    os.fsync(fout)
    fout.close()
    if TESTING():
        try:
            os.chmod(invoice_path, 0666)
        except:
            pass
    _, invoice_file_name = os.path.split(invoice_path)
    return invoice_file_name


def readTransaction(invoice, success=''):
    """
    find transaction. return (email, trans_date, domains) or None
    if transaction was found, put success result inside.
    """
    tran_path = sessions_dir_path() + invoice
    if not os.path.exists(tran_path):
        return None
    fin = open(tran_path, 'r')
    fsrc = fin.read()
    fin.close()
    first_line = fsrc.split('\n')[0]
    if success != '':
        fsrc += '\n' + success
        tran_path_tmp = tran_path + ".new"
        f = open(tran_path_tmp, "wb")
        f.write(fsrc)
        f.flush()
        os.fsync(f.fileno())
        f.close()
        os.rename(tran_path_tmp, tran_path)
    split_res = first_line.split('>>>')
    if len(split_res) < 3:
        return None
    return split_res


def isTransactionDeclined(invoice):
    tran_path = sessions_dir_path() + invoice
    if not os.path.exists(tran_path):
        return None
    fin = open(tran_path, 'r')
    fsrc = fin.read()
    fin.close()
    if len(fsrc.split('\n')) < 2:
        return None
    second_line = fsrc.split('\n')[1]
    if second_line.startswith('declined>>>'):
        return True
    if second_line.startswith('failed>>>'):
        return True
    return None


def checkTransaction(invoice):
    """
    is transaction successful?
    returns: (user, trans_date, domains_list_string)
    """
    tran_path = sessions_dir_path() + invoice
    if not os.path.exists(tran_path):
        return None

    fin = open(tran_path, 'r')
    fsrc = fin.read()
    fin.close()

    if len(fsrc.split('\n')) < 2:
        return None

    first_line = fsrc.split('\n')[0]
    second_line = fsrc.split('\n')[1]

    if not second_line.startswith('successful>>>'):
        return None

    first_line_words = first_line.split('>>>')
    second_line_words = second_line.split('>>>')

    if len(first_line_words) < 3:
        return None
    if len(second_line_words) < 2:
        return None

    first_line_words[1] = second_line_words[1]

    return first_line_words

#------------------------------------------------------------------------------
#--- USER BALANCE
#------------------------------------------------------------------------------

def addBalancePayment(info_string, email='', trans_date=formatdate(), success=""):
    if not os.path.isdir(balance_transactions_dir_path()):
        try:
            os.makedirs(balance_transactions_dir_path())
        except:
            pass
    invoice_file_num, invoice_path = tempfile.mkstemp("", "", balance_transactions_dir_path())
    fout = os.fdopen(invoice_file_num, "w")
    os.fsync(fout)
    fout.close()
    _, invoice_file_name = os.path.split(invoice_path)
    fout = open( invoice_path, "a")
    fout.write(email + '>>>' + trans_date + '>>>' + info_string)
    if success != '':
        fout.write('\n' + success)
    os.fsync(fout)
    fout.close()
    if TESTING():
        try:
            os.chmod(invoice_path, 0666 )
        except:
            pass
    return invoice_file_name


def checkBalancePayment(invoice):
    """
    is transaction successful?
    returns: (user, trans_date, domains_list)
    """
    tran_path = balance_transactions_dir_path() + invoice
    if not os.path.exists(tran_path):
        return None

    fin = open(tran_path, 'r')
    fsrc = fin.read()
    fin.close()

    if len(fsrc.split('\n')) < 2:
        return None

    first_line = fsrc.split('\n')[0]
    second_line = fsrc.split('\n')[1]

    if not second_line.startswith('successful'):
        return None

    first_line_words = first_line.split('>>>')

    if len(first_line_words) < 3:
        return None

    return first_line_words

#-------------------------------------------------------------------------------
# SESSIONS
#-------------------------------------------------------------------------------

def addSession(login):
    prefixS = time.strftime("S%Y%m%d.")
    session_file_num, session_path = tempfile.mkstemp("", prefixS, sessions_dir_path())
    fout = os.fdopen( session_file_num, "w")
    fout.write(login.strip().lower() + '\n')
    os.fsync(fout)
    fout.close()
    session_name = os.path.split(session_path)[1]
    return session_name


def readSession(session):
    session_path = sessions_dir_path() + session
    if not os.path.exists(session_path):
        return None

    fin = open(session_path, 'r')
    fsrc = fin.read()
    fin.close()

    lines = fsrc.split('\n')
    if len(lines) == 0:
        return None

    return lines[1:]


def transactionSuccess(domains_list, tran_id):
    tran_path = sessions_dir_path() + tran_id
    if not os.path.exists(tran_path):
        return False

    fout = open( tran_path, "a" )
    fout.write('pass\n')
    for domain in domains_list.split(';'):
        if domain.strip() == '':
            continue
        fout.write(domain + '>>>' + formatdate(time.time(), True))
    fout.flush()
    os.fsync(fout)
    fout.close()

    return True

#-------------------------------------------------------------------------------

def writeLoginLog(login):
    ip_addr = cgi_escape(os.environ.get('REMOTE_ADDR', '0.0.0.0'))
    fout = open(login_log_file_path(), 'a')
    fout.write(formatdate() + ' [' + ip_addr + '] {' + login + '}\n')
    fout.close()


def readLogForEmail(email):
    iplist = {}
    fin = open(login_log_file_path(), 'r')
    logsrc = fin.read()
    fin.close()
    loglines = logsrc.split("\n")
    for line in loglines:
        if line.strip() == '':
            continue
        user = ''
        res = re.search('\{(.*)\}', line)
        if res is not None:
            user = res.group(1)
        if user == '':
            continue
        if user.lower().strip() != email.lower().strip():
            continue
        ip = ''
        res = re.search('\[(.*)\]', line)
        if res is not None:
            ip = res.group(1)
        if ip != '':
            iplist[ip] = ''
    return iplist

#-------------------------------------------------------------------------------
# PROTECTION
#-------------------------------------------------------------------------------

def protection(data, cookie):
    from domains import make_msg
    from html_data import (
        ph,
        printLoginPage,
        need2wait_pay100_html,
        pay100_html,
        input_verification_code_html,
        register_new_user_html,
        wrong_arguments_html,
    )
    login = data['login']
    ip_addr = cgi_escape(os.environ.get('REMOTE_ADDR', '0.0.0.0'))
    open(protection_log_file_path(), 'a').write('%s    %s    %s\n' % (login, time.asctime(), ip_addr))
    if os.path.isfile(maintanance_mode_users_list_file()):
        super_users = open(maintanance_mode_users_list_file(), 'r').read().strip().split()
        if login not in super_users:
            open(protection_log_file_path(), 'a').write('access restricted only for super users in "%s"\n' % (
                maintanance_mode_users_list_file()))
            killCookie(cookie)
            data['msg'] = make_msg('Website is currently under maintenance mode, thanks for your patience.')
            ph()
            printLoginPage(data)
            return False
    uinfo = {}
    if not read_info(login, uinfo):
        open(protection_log_file_path(), 'a').write('Reading user info failed.\n')
        killCookie(cookie)
        data['msg'] = make_msg('Reading user info failed.')
        ph()
        printLoginPage(data)
        return False

    pay100_flag = 'pay100date' in uinfo
    fullinfo_flag = 'fax' in uinfo and 'phone' in uinfo and 'address' in uinfo
    verify_count = 0
    if 'verif_fax' in uinfo:
        verify_count += 1
    if 'verif_mail' in uinfo:
        verify_count += 1
    if 'verif_phone' in uinfo:
        verify_count += 1
    verify_flag = False
    if verify_count == 3:
        verify_flag = True

    if 'trust_instant' in uinfo:
        pay100_flag = True
        verify_flag = True
        fullinfo_flag = True

    else:
        dtm = parsedate(uinfo.get('datetime', ''))
        if dtm is not None:
            t_trust = datetime.datetime.fromtimestamp(time.mktime(dtm))
            t_now = datetime.datetime.fromtimestamp(time.time())
            dt = t_now - t_trust
            days2wait = 87 - 30 * verify_count
            if dt.days < days2wait:
                verify_flag = False
                t_3month = t_trust + datetime.timedelta(days=days2wait)
                data['date3month'] = t_3month.strftime("%d %B %Y")

    if not pay100_flag:
        #print pay 100$ page
        if 'new_id' in data and data['new_id'] == '1':
            tdelay = getTransactionDelay(login)
            if not TESTING():
                if tdelay < 60 * 60 * 2:  # 2 hours
                    data['time2wait'] = str(60 * 2 - int(tdelay / 60.0))
                    open(protection_log_file_path(), 'a').write('pay100=false, need to wait 2 hours to pay 100$\n')
                    print cookie
                    ph()
                    print need2wait_pay100_html(data)
                    return
            invoice = addTransaction('register', login)
            uinfo['last_transaction_time'] = formatdate(time.time(), True)
            uinfo['pay100id'] = invoice
            save_info(login, uinfo)
            open(protection_log_file_path(), 'a').write('pay100=false, new_id=1, generated new transaction to pay 100$: %s\n' % invoice)
        if 'pay100id' not in uinfo:
            invoice = addTransaction('register', login)
            uinfo['last_transaction_time'] = formatdate(time.time(), True)
            uinfo['pay100id'] = invoice
            save_info(login, uinfo)
            open(protection_log_file_path(), 'a').write('pay100=false, generated new transaction to pay 100$: %s\n' % invoice)
        data['invoice'] = uinfo['pay100id']
        data['tran_id'] = uinfo['pay100id']
        open(protection_log_file_path(), 'a').write('pay100=false, need to pay 100$\n')
        print cookie
        ph()
        print pay100_html(data)
        return False

    if pay100_flag and not verify_flag:
        #print verification page
        if 'verif_fax' in uinfo:
            data['fax_state'] = '<font color=green> done </font>'
        if 'verif_phone' in uinfo:
            data['phone_state'] = '<font color=green> done </font>'
        if 'verif_mail' in uinfo:
            data['mail_state'] = '<font color=green> done </font>'
        data['msg'] = """
Hello! <br>
You have been trusted to get access to AI Domains.<br>
But we would like to wait for 3 month before we give you full access.
However, you can decrease this period if you input verification codes we sent you.
<br>"""
        if 'date3month' in data:
            data['msg'] += 'You will be granted access to domains registry at : ' + data['date3month']
        open(protection_log_file_path(), 'a').write('pay100=true, verify=false, input verification code\n')
        ph()
        print input_verification_code_html(data)
        return False

    if not fullinfo_flag:
        #ask for info page
        data['readonly'] = 'readonly="readonly"'
        data['email'] = data['login']
        data['startinfo'] = "Hello! Please fill this form."
        data['msg'] = ''
        open(protection_log_file_path(), 'a').write('fullinfo=false, please fill this form\n')
        ph()
        print register_new_user_html(data)
        return False

    if pay100_flag and verify_flag and fullinfo_flag:
        open(protection_log_file_path(), 'a').write('pay100=true verify=true fullinfo=true\n')
        return True

    ph()
    print wrong_arguments_html
    return False


def hit_ip_address(ip, mode='a', ip_filter_folder=ip_filter_dir()):
    ip_filepath = os.path.join(ip_filter_folder, ip.replace('.', '_'))
    fout = open(ip_filepath, mode)
    fout.write('%d\n' % int(time.time()))
    fout.flush()
    os.fsync(fout)
    fout.close()


def ip_address_filter(current_ip='', ip_filter_folder=ip_filter_dir()):
    if not current_ip:
        try:
            current_ip = cgi_escape(os.environ.get('REMOTE_ADDR', '0.0.0.0')).strip()
        except:
            return False
    if not os.path.isdir(ip_filter_folder):
        return False
    ip_filepath = os.path.join(ip_filter_folder, current_ip.replace('.', '_'))
    if not os.path.isfile(ip_filepath):
        # create a new file with only one record
        hit_ip_address(current_ip, mode='w', ip_filter_folder=ip_filter_folder)
        return False
    fin = open(ip_filepath, 'r')
    hits = fin.read().splitlines()
    fin.close()
    if len(hits) < 10:
        # append a record to existing file
        hit_ip_address(current_ip, ip_filter_folder=ip_filter_folder)
        return False
    try:
        if int(time.time()) - int(hits[0]) > 10 * 60:
            # after 10 minutes we can rewrite current counters
            hit_ip_address(current_ip, mode='w', ip_filter_folder=ip_filter_folder)
            return False
    except:
        return True
    # more than 10 hits during last 10 minutes : filter out this!
    return True
