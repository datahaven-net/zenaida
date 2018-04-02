# zenaida

Open source domain registry system built on top of EPP protocol



## Get Started

Clone project files locally. If you are running on production server please use user "zenaida" and run all applications on behalf of that user:

        sudo su zenaida
        cd ~
        git clone https://github.com/datahaven-net/zenaida.git
        cd zenaida


Install postgress and few other packages:

        sudo apt-get install python-pip python-dev libpq-dev postgresql postgresql-contrib


Create DB and user:

        sudo su - postgres

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


To be abe to run same code on production machine as well as locally on your laptop you can use isolated development settings, configure this by setting src/main/params.py file:

        cp src/main/params.example.py src/main/params.py
        nano src/main/params.py


Set those settings in your params.py if you starting a new production machine:

        ENV = 'production'
        DATABASES_ENGINE = 'django.db.backends.postgresql_psycopg2'
        DATABASES_NAME = 'zenaida_db_01'
        DATABASES_USER = 'zenaida_db_user'
        DATABASES_PASSWORD = '<password>'
        DATABASES_HOST = 'localhost'
        DATABASES_PORT = ''


To run locally you can use SQLite3:

        ENV = 'development'
        DATABASES_ENGINE = 'django.db.backends.sqlite3'
        DATABASES_NAME = 'db.sqlite'


Create virtual environement if you do not have yet:

        make venv


Run Django migrate process:

        make migrate


Launch Django server to test the configuration:

        make runserver


Now you can navigate your browser to http://127.0.0.1:8000/ and see the web site running locally.




## Requirements Handling

The project has automated handling of production requirements, the idea behind it is that
you should always use the latest versions of every requirement, a Makefile target is in place
to update the `requirements.txt` file (`make requirements.txt` will do).

In case you need a specific version of a library, the protocol should be:

* Place the needed fixed version using pip notation in any of the requirements/* files
* Put a comment over the fixed requirement explaining the reason for fixing it (usually with a link to an issue/bug)
* Run `make requirements.txt`, the resulting requirements file will include the fixed version of the package

For some more advanced uses, a manual edit of the requirements.txt can be done but make sure to document it somewhere because
`make requirements.txt` *will* overwrite this file.


# Testing against latest versions

By default, `tox` and `make test` will only test against production requirements, in order to test against latest versions of the dependencies, there are two tox environments, `latest27` and `latest35`.

They can be run via `tox -e latest27,latest35` or also with `make test_latest`
