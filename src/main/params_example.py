from __future__ import unicode_literals

#--- Django
ENV = 'development'
# ENV = 'production'
# ENV = 'docker'
# DEBUG = True
# RAISE_EXCEPTIONS = True
# SECRET_KEY = 'must be declared here !!!'
# SITE_BASE_URL = ''

#--- Log files permission fix
import os
os.umask(0o002)

#--- SQlite3
# DATABASES_ENGINE = 'django.db.backends.sqlite3'
# DATABASES_NAME = 'db.sqlite'

#--- Oracle
# DATABASES_ENGINE = 'django.db.backends.oracle'
# DATABASES_NAME = 'xe'
# DATABASES_USER = 'system'
# DATABASES_PASSWORD = '<password>'
# DATABASES_HOST = 'localhost'
# DATABASES_PORT = '49161'
# DATABASES_OPTIONS = {}
# DATABASES_TEST = dict(NAME='unittest.db')
# DATABASES_CONN_MAX_AGE = 0

#--- Postgres
# DATABASES_ENGINE = 'django.db.backends.postgresql_psycopg2'
# DATABASES_NAME = 'zenaida_db_01'
# DATABASES_USER = 'zenaida_db_user'
# DATABASES_PASSWORD = '<password>'
# DATABASES_HOST = 'localhost'
# DATABASES_PORT = ''

#--- Database Backups
# DBBACKUP_STORAGE_OPTIONS = {'location': '/tmp'}

#--- EMAIL
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = 'your_account@gmail.com'
# EMAIL_HOST_PASSWORD = 'password is secret'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False
# EMAIL_ADMIN = f'admin@{SITE_BASE_URL}'

#--- Smoketest settings
# SMOKETEST_HOSTS = ["http://example.com"]
# SMOKETEST_MAXIMUM_UNAVAILABLE_AMOUNT = 3

#--- Brute force protection settings
# BRUTE_FORCE_PROTECTION_ENABLED = False
# BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_KEY_PREFIX = 'domain_lookup_brute_force'
# BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_MAX_ATTEMPTS = 15
# BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_TIMEOUT = 60*15

#--- Google reCaptcha Keys
# GOOGLE_RECAPTCHA_SECRET_KEY = 'dummy_secret_key'
# GOOGLE_RECAPTCHA_SITE_KEY = 'dummy_site_key'

#--- Zenaida configuration 
# ZENAIDA_REGISTRAR_ID = 'zenaida_registrar'
# ZENAIDA_SUPPORTED_ZONES = []

# ZENAIDA_RABBITMQ_CLIENT_CREDENTIALS_FILENAME = '/home/zenaida/keys/rabbitmq_client_credentials.txt'
# ZENAIDA_GATE_HEALTH_FILENAME = '/home/zenaida/health'

# ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS = 5
# ZENAIDA_DOMAIN_PRICE = 100.0
# ZENAIDA_DOMAIN_RESTORE_PRICE = 200.0

#--- Zenaida 4CS Online payments
# ZENAIDA_BILLING_4CSONLINE_MERCHANT_ID = ''
# ZENAIDA_BILLING_4CSONLINE_MERCHANT_LINK = 'https://merchants.4csonline.com/TranSvcs/tp.aspx'
# ZENAIDA_BILLING_4CSONLINE_MERCHANT_VERIFY_LINK = 'https://merchants.4csonline.com/TranSvcs/tqs.aspx'
# ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION = False
# ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION = False
# ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE = 0.0


#--- Zenaida BTCPay Settings
# ZENAIDA_BTCPAY_CLIENT_PRIVATE_KEY = ""
# ZENAIDA_BTCPAY_MERCHANT = ""
# ZENAIDA_BTCPAY_HOST = ""

#--- Zenaida BTCPayServer payments
# ZENAIDA_BILLING_BTCPAY_MERCHANT_LINK = 'https://node.bitcoin.ai'

#--- SMS Gateway configuration
# SMS_GATEWAY_AUTHORIZATION_BEARER_TOKEN = 'bearer'
# SMS_GATEWAY_SEND_URL = 'https://api.clickatell.com/rest/message'

#--- Push notification service configuration
# PUSH_NOTIFICATION_SERVICE_POST_URL = 'https://api.pushover.net/1/messages.json'
# PUSH_NOTIFICATION_SERVICE_API_TOKEN = ''
# PUSH_NOTIFICATION_SERVICE_USER_TOKEN = ''

#--- Alerts
# ALERT_SMS_PHONE_NUMBERS = []
# ALERT_EMAIL_RECIPIENTS = []

#--- Account & Auth
# ACTIVATION_CODE_EXPIRING_MINUTE = 15

#--- Admin Panel Restrictions
# RESTRICT_ADMIN = True
# ALLOWED_ADMIN_IPS = ['127.0.0.1', '::1']
# ALLOWED_ADMIN_IP_RANGES = ['127.0.0.0/24', '::/1']
# RESTRICTED_APP_NAMES = ['admin']
# TRUST_PRIVATE_IP = True
