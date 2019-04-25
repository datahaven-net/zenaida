from __future__ import unicode_literals

#--- Django
ENV = 'development'
# ENV = 'production'
# DEBUG = True
# RAISE_EXCEPTIONS = True
# SECRET_KEY = 'must be declared here !!!'


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


#--- EMAIL
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = 'your_account@gmail.com'
# EMAIL_HOST_PASSWORD = 'password is secret'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False


#--- Google reCaptcha Keys
# GOOGLE_RECAPTCHA_SECRET_KEY = 'dummy_secret_key'
# GOOGLE_RECAPTCHA_SITE_KEY = 'dummy_site_key'


#--- Zenaida configuration 
# ZENAIDA_REGISTRAR_ID = 'zenaida_registrar'
# ZENAIDA_SUPPORTED_ZONES = ['com', 'net', 'org', 'ai', ]

# ZENAIDA_RABBITMQ_CLIENT_CREDENTIALS_FILENAME = '/home/zenaida/keys/rabbitmq_client_credentials.txt'
# ZENAIDA_EPP_LOG_FILENAME = '/home/zenaida/logs/epp.log'
# ZENAIDA_AUTOMATS_LOG_FILENAME = '/home/zenaida/logs/automats.log'
# ZENAIDA_GATE_HEALTH_FILENAME = '/home/zenaida/health'

# ZENAIDA_BILLING_BYPASS_PAYMENT_TIME_CHECK = False

#--- Zenaida 4CS Online payments
# ZENAIDA_BILLING_4CSONLINE_MERCHANT_ID = ''
# ZENAIDA_BILLING_4CSONLINE_MERCHANT_LINK = 'https://merchants.4csonline.com/TranSvcs/tp.aspx'
# ZENAIDA_BILLING_4CSONLINE_MERCHANT_VERIFY_LINK = 'https://merchants.4csonline.com/TranSvcs/tqs.aspx'
# ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_VERIFICATION = False
# ZENAIDA_BILLING_4CSONLINE_BYPASS_PAYMENT_CONFIRMATION = False

#--- Zenaida BTCPayServer payments
# ZENAIDA_BILLING_BTCPAY_MERCHANT_LINK = 'https://node.bitcoin.ai'
