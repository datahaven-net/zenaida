

Install postgress:

        sudo apt-get install python-pip python-dev libpq-dev postgresql postgresql-contrib


Create DB and user:

        veselin@test:~$ sudo su - postgres
        postgres@test:~$ psql
        psql (9.3.22)
        Type "help" for help.

        postgres=# CREATE DATABASE zenaida_db_01;
        CREATE DATABASE
        postgres=# CREATE USER zenaida_db_user WITH PASSWORD '<password>';
        CREATE ROLE
        postgres=# ALTER ROLE zenaida_db_user SET client_encoding TO 'utf8';
        ALTER ROLE
        postgres=# ALTER ROLE zenaida_db_user SET default_transaction_isolation TO 'read committed';
        ALTER ROLE
        postgres=# ALTER ROLE zenaida_db_user SET timezone TO 'UTC';
        ALTER ROLE
        postgres=# GRANT ALL PRIVILEGES ON DATABASE zenaida_db_01 TO zenaida_db_user;
        GRANT
        \q
        exit


Setup params.py:

        cd /home/zenaida/zenaida/src/main/
        cp params.example.py params.py
        nano params.py


Set those settings in your params.py :

        ENV = 'prod'
        DATABASES_ENGINE = 'django.db.backends.postgresql_psycopg2'
        DATABASES_NAME = 'zenaida_db_01'
        DATABASES_USER = 'zenaida_db_user'
        DATABASES_PASSWORD = '<password>'
        DATABASES_HOST = 'localhost'
        DATABASES_PORT = ''


Create virtual environement if you do not have yet:

        make venv


Run Django migrate process:

        make migrate


