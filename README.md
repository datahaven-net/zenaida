# Zenaida

Open source domain registry system built on top of EPP protocol.
Zenaida works as a "client" for EPP registry back-end system and provides on-line service for end-users who wish to register domains.
Tested together with CoCCA backend software: https://cocca.org.nz/



## Get Started

Clone project files locally. If you are running on production server please use user `zenaida` and run all applications on behalf of that user:

        sudo adduser zenaida
        sudo usermod -aG sudo zenaida
        sudo su zenaida
        cd ~
        git clone https://github.com/datahaven-net/zenaida.git
        cd zenaida


Install required packages:

        sudo apt-get install make python3-pip python3-dev python3-venv libpq-dev postgresql postgresql-contrib memcached uwsgi-plugins-all

 
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


To be able to run same code on production machine as well as locally on your laptop you can use isolated development settings, configure this by setting `src/main/params.py` file:

        cp src/main/params_example.py src/main/params.py
        nano src/main/params.py


Set those settings in your `params.py` file if you starting a new production machine:

        ENV = 'production'
        DATABASES_ENGINE = 'django.db.backends.postgresql'
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


Run Django migrate command:

        make migrate


Run Django collectstatic command:

        make collectstatic


Create Django super user:

        make createsuperuser


Launch Django server to test the configuration:

        make runserver


Now you can navigate your browser to `http://127.0.0.1:8000/` and visit Zenaida web site which is running locally.



## Running on production

For production configuration you can take a look at some examples in `etc/` folder.

You might want to use your own tweaks for nginx and uwsgi, so those files are just a starting point for you.
Configuration here was tested on Ubuntu 18.04.1 LTS server.

First lets create a separate folder to store all interesting logs in one place and configure log rotation:

        mkdir /home/zenaida/logs/
        sudo chown www-data:zenaida -R /home/zenaida/logs/
        sudo cp etc/logrotate.d/zenaida /etc/logrotate.d/


Add `www-data` user to `zenaida` group so uwsgi process will be able to access log files created by Django:

        sudo usermod -a -G zenaida www-data


Make sure you set the correct domain name on your server:

        sudo hostname -b yourdomain.com


Install nginx if you do not have it yet installed:

        sudo apt-get install nginx


Activate nginx site configuration by creating a sym-link:

        cp etc/nginx/zenaida.example etc/nginx/zenaida
        sudo ln -s /home/zenaida/zenaida/etc/nginx/zenaida /etc/nginx/sites-enabled/
        sudo unlink /etc/nginx/sites-enabled/default


To secure your site you need to configure SSL certificate. Check `etc/nginx/zenaida` file to configure crtificate and key files location. Here is an example SSL config you can use to build your setup:

        ssl_certificate     /home/zenaida/ssl/zenaida.crt;
        ssl_certificate_key /home/zenaida/ssl/zenaida.key;
        ssl_ciphers         EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH;
        ssl_protocols       TLSv1.1 TLSv1.2;


Now it is time to configure uwsgi in emperor mode to follow best practices.
We will need one vassal to be running and serving Zenaida traffic.
The main uwsgi emperor process will be starting as systemd service:

        cp etc/systemd/system/uwsgi-emperor.service.example etc/systemd/system/uwsgi-emperor.service
        sudo ln -s /home/zenaida/zenaida/etc/systemd/system/uwsgi-emperor.service /etc/systemd/system/
        

Now start uwsgi emperor service:

        sudo systemctl start uwsgi-emperor.service


You can always check current situation with:

        systemctl status uwsgi-emperor.service


Finally restart nginx server to make everything work end-to-end:

        sudo service nginx restart


At any moment you can gracefully respawn Zenaida process manually by "touching" zenaida.ini file:

        touch /home/zenaida/zenaida/etc/uwsgi/vassals/zenaida.ini


Your live server should be up and running now, navigate your browser to http://www.yourdomain.com

But you will need a to do a bit more configurations on Production server later on, read more about that bellow after you finish preparing other parts of the system.



## Django settings

In the file `src/main/params.py` you will have to set few important variables. Those settings are specific for your host machine and can not be stored in the source code. Also this file is a place to store keys, passwords, etc.

Other settings in `params.py` file also described in that document, but here is a list of most important settings:

* `ENV = 'production'` : this will identify your production machine
* `DEBUG = False` : must be always `False` on your production machine
* `SITE_BASE_URL = 'https://yourdomain.com'` : domain name of your host
* `SECRET_KEY = 'xxxx'` : django key to be used to encrypt user sessions, must be 50 bytes long
* `ZENAIDA_REGISTRAR_ID = 'registrar_abc'` : name of your registrar to be used to connect to CoCCA back-end
* `ZENAIDA_SUPPORTED_ZONES = ['net', 'com', 'org', ]` : list of supported domain zones



## Install Perl and required modules

To establish connection between Zenaida and EPP registry system we use couple more components:

* RabbitMQ server to run messaging queue and exchange EPP commands
* Perl script which runs in background and keep alive connection with EPP server
* Python Polling job which periodically request updates from EPP server for backward synchronization   


Lets start from installing Perl and required modules on Zenaida machine.
Few binary dependencies are required to running Perl modules:

        sudo apt-get install build-essential libxml2-dev libnet-ssleay-perl libssl-dev libdigest-sha1-perl


Then we need to check if CPAN Perl package manager is installed and configured on your OS - it should be
present on most Linux systems by default after installing `build-essential` package:

        cpan


Installing Perl modules is easy, but takes some time:

        sudo cpan install AnyEvent TryCatch JSON XML::LibXML Method::Signatures Digest::MD5 Data::Dumper HTTP::Daemon  Net::RabbitFoot Net::Server::PreFork Net::EPP::Simple


If that fails you can also try to use `cpanminus` to do the same:

        sudo apt-get install cpanminus
        sudo cpanm -i --notest AnyEvent TryCatch JSON XML::LibXML Method::Signatures Digest::MD5 Data::Dumper HTTP::Daemon  Net::RabbitFoot Net::Server::PreFork Net::EPP::Simple



## Install and configure RabbitMQ

RabbitMQ is used to drive a EPP messaging queue between Zenaida host and EPP registry system.

Use Apt package manager to install RabbitMQ server on your Zenaida host:

        echo "deb https://www.rabbitmq.com/debian testing main" | sudo tee /etc/apt/sources.list.d/rabbitmq.list
        wget -O- https://www.rabbitmq.com/rabbitmq-release-signing-key.asc | sudo apt-key add -
        sudo apt-get update
        sudo apt-get install rabbitmq-server
        sudo rabbitmq-plugins enable rabbitmq_management


We need to have secure way to access RabbitMQ administrator panel, so lets create a separate user account for that purpose:

        sudo rabbitmqctl add_user zenaida <password 1>
        sudo rabbitmqctl set_user_tags zenaida administrator
        sudo rabbitmqctl set_permissions -p / zenaida ".*" ".*" ".*"


Another user account we will use for EPP message queue between Zenaida and EPP registry:

        sudo rabbitmqctl add_user zenaida_epp <password 2>
        sudo rabbitmqctl set_permissions -p / zenaida_epp ".*" ".*" ".*"


Now you can navigate your web browser to RabbitMQ dashboard at `http://www.yourdomain.com:15672` and
login with `zenaida`:`<password 1>` administrative credentials you have just created.

You can verify permissions of RabbitMQ users - must be 3 users existing:

* guest
* zenaida
* zenaida_epp


We advise you to remove "guest" user because of security concerns.

More details about RabbutMQ installation you can find here: https://www.rabbitmq.com/install-debian.html

To install RabbutMQ on MacOS refer to that page: https://www.rabbitmq.com/install-standalone-mac.html

For local development you might want to run RabbutMQ manually instead of starting it as a system service.
In that case you just run a local server from Makefile and then you can open RabbitMQ dashboard at `http://localhost:15672`:

        make rabbitmq_server_dev



## Establish connection with EPP registry

To run real-time connection between Zenaida and EPP registry system a separate process was developed which is called "EPP Gate".
You will find this Perl script in `bin/epp_gate.pl` file.

To be able to start EPP Gate process you need to provide it with required credentials for EPP registry and RabbitMQ - example files you can find in `etc/` folder.
You can place those files in a safe place on your server and fill with correct credentials:

        mkdir /home/zenaida/keys/
        echo "localhost 5672 zenaida_epp <password 2>" > /home/zenaida/keys/rabbitmq_gate_credentials.txt


EPP regisrty will have to also provide you with credentials to access EPP server remotely.
Place them in another file in your `keys` folder:

        echo "epp.yourdomain.com 700 <epp_user> <epp_password>" > /home/zenaida/keys/epp_credentials.txt


Before continue further make sure you decreased access permissions to your secrets:

        chmod go-rwx -R /home/zenaida/keys/


Now we need to be sure that EPP connection is configured correctly. First read bellow about how to configure `ZENAIDA_RABBITMQ_CLIENT_CREDENTIALS_FILENAME` setting in your `src/main/params.py` file. This is necessary to be able to connect Django with RabbitMQ.

Now lets execute Perl script directly:

        perl bin/epp_gate.pl /home/zenaida/keys/epp_credentials.txt /home/zenaida/keys/rabbitmq_gate_credentials.txt
        ...
        Sat May 19 20:49:17 2018: Connecting to RabbitMQ server at localhost:5672 with username: <rabbitmq_user>
        Sat May 19 20:49:17 2018:  [x] Awaiting RPC requests


Keep it running in the current terminal and open another console window to be able to fire real-time EPP requests towards given EPP server:

        venv/bin/python -c 'import sys, os, django; sys.path.append("src/"); os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings"); django.setup(); import zen.zclient; print(zen.zclient.cmd_domain_check(["testdomain.com", ]))'


If RabbitMQ and Zenaida Gate process was configured correctly you should see a json response from EPP Gate like that:

        {'epp': {'@{http://www.w3.org/2001/XMLSchema-instance}schemaLocation': 'urn:ietf:params:xml:ns:epp-1.0 epp-1.0.xsd', 'response': {'result': {'@code': '1000', 'msg': 'Command completed successfully'}, 'resData': {'chkData': {'@{http://www.w3.org/2001/XMLSchema-instance}schemaLocation': 'urn:ietf:params:xml:ns:domain-1.0 domain-1.0.xsd', 'cd': {'name': {'@avail': '1', '#text': 'testdomain.com'}}}}, 'trID': {'clTRID': '103513f75a176e56038b2244258357f7', 'svTRID': '1526756418267'}}}}



## Configure Zenaida Gate as a systemd service

To be able to easily manage Zenaida Gate process on your host system you can add it to your systemd scripts.

Zenaida Gate service consist of 3 units:

* `zenaida-gate.service` : service which executes Perl script and keep it running non-stop
* `zenaida-gate-watcher.service` : background service which is able to "restart" `zenaida-gate.service` when required
* `zenaida-gate-health.path` : systemd trigger which is monitoring `/home/zenaida/health` file for any modifications and notify `zenaida-gate-watcher.service`

Those three units are required to have Zenaida Gate auto-healing mechanism running all the time. When CoCCA back-end drops connection on server-side Zenaida Gate needs to be "restarted". We must re-login to be able to send EPP messages again - this is done inside Perl script and login flow will be initiated automatically.

You can configure systemd Zenaida Gate service this way:

        mkdir -p /home/zenaida/.config/systemd/user/
        cp etc/systemd/system/zenaida-gate.service.example /home/zenaida/.config/systemd/user/zenaida-gate.service
        cp etc/systemd/system/zenaida-gate-watcher.service.example /home/zenaida/.config/systemd/user/zenaida-gate-watcher.service
        cp etc/systemd/system/zenaida-gate-health.path.example /home/zenaida/.config/systemd/user/zenaida-gate-health.path
        systemctl --user enable zenaida-gate.service
        systemctl --user enable zenaida-gate-watcher.service
        systemctl --user enable zenaida-gate-health.path


Then you just need to start all services in a such way:

        systemctl --user start zenaida-gate.service
        systemctl --user start zenaida-gate-watcher.service
        systemctl --user start zenaida-gate-health.path


You can always check current situation with:

        systemctl --user status zenaida-gate.service


Also you can check services logs to see full history:

        journalctl -f -u user@`id -u`.service


Now if you have access to CoCCA backend you can test auto-healing mechanism by simply dropping EPP session on server side and keep monitoring `/home/zenaida/logs/gate.log` output file.

Also you can perform manual test locally - just modify `/home/zenaida/health` file and Zenaida Gate suppose to be restarted automatically.



## Configure Zenaida Poll systemd service

In order to receive notifications back from CoCCA backend another script was developed and wrapped into systemd service called `zenaida-poll.service`.

This job runs in background and sends EPP `poll_req` and `poll_ack` commands periodically towards CoCCA and this way receives notifications about domains, contacts or nameservers modifications done directly on backend.

You can configure and start systemd Zenaida Poll service this way:

        cp etc/systemd/system/zenaida-poll.service.example /home/zenaida/.config/systemd/user/zenaida-poll.service
        systemctl --user enable zenaida-poll.service
        systemctl --user start zenaida-poll.service



## Connect Django with CoCCA via Zenaida Gate

Now it is time to configure access to EPP Gate from Django side - it will use RabbitMQ server as a client to send/receive EPP XML messages.

First place your RabbitMQ client credentials in another file in your `/home/zenaida/keys-www-data` folder.

Here is a small exception, because those credentials must be accessable from django software running on behalf of www-data user and nginx+uwsgi process ... 
In a previous step credentials for `zenaida-gate` service must be only accessable by `zenaida` user so we store them in `/home/zenaida/keys` folder with more restrictive permissions.

First you create a new JSON-formatted file like that to hold your RabbitMQ client credentials:

###### /tmp/rabbitmq_client_conf.json

    {
        "host": "localhost",
        "port": "5672",
        "username": "zenaida",
        "password": "<password 1>,
        "timeout": 20,
        "queue_name": "epp_rpc_messages"
    }


To mitigate risks you can put those credentials in a separate folder with dedicated access from your Django application.

        mkdir /home/zenaida/keys-www-data/
        mv /tmp/rabbitmq_client_conf.json /home/zenaida/keys-www-data/
        sudo chown www-data -R /home/zenaida/keys-www-data/


Edit file `src/main/params.py` and add such line:

        ZENAIDA_RABBITMQ_CLIENT_CREDENTIALS_FILENAME = '/home/zenaida/keys-www-data/rabbitmq_client_conf.json'


You know, you can try to play with multiple console terminals running in parallel to see all stuff connected and run smoothly.

If you are developing locally and started Zenaida application directly on your local OS you can run such command to start EPP Gate:

        make epp_gate_dev


If all components was set up correctly and running right now on your machine you should be able to use most of Zenaida functionality now.
For example you can lookup some domains by going to `http://www.yourdomain.com/lookup/` (or `http://localhost:8000/lookup/` if running locally)
in your web browser and use Domain Search form to test it.



## Configure Email settings

If it is required you cat enable user account activations via email. To do that edit file `src/main/params.py` and add such line:

        ENABLE_USER_ACTIVATION = True


Also you have to configure outgoing email channel to deliver messages. Different backends can be used in Django, simplest way to start with Google Accounts SMTP service:

        EMAIL_HOST = 'smtp.gmail.com'
        EMAIL_HOST_USER = 'my_gmail_login@gmail.com'
        EMAIL_HOST_PASSWORD = '<password>'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_USE_SSL = False



## Configure Memcache

TODO: memcached...



## Configure Googla Captcha

If you want users to see Google Captcha in login screen, you need to go to https://www.google.com/recaptcha/ and setup captcha for your website.
In order to setup, you can check Google documentation here: https://developers.google.com/recaptcha

Once you have site key and secret key for your website, you should edit `src/main/params.py` file and set `GOOGLE_RECAPTCHA_SITE_KEY` and `GOOGLE_RECAPTCHA_SECRET_KEY` constants.

If you don't want to enable Google captcha for your local environment or for your website, you can set `GOOGLE_RECAPTCHA_SITE_KEY = None`.



## Configure BTCPayServer

TODO:



## Database Backups

In params.py file, storage location should be defined.

        DBBACKUP_STORAGE_OPTIONS = {'location': '/tmp/'}

To backup your database, use below Django command.

        ./venv/bin/python manage.py dbbackup

 To restore latest backup for database, use below Django command.

        ./venv/bin/python manage.py dbrestore

There are more options to use for database backups like compressing, encrypyting etc.
Go to [django-dbbackup](https://django-dbbackup.readthedocs.io/en/stable/commands.html) documentation for more info.



## Importing domains from CSV file

It is possible to export multiple domains details from CoCCA server dashboard into single .csv file. Zenaida can read such format and load those domains easily. This way you can run initial import before GoLive with new Zenaida web-site:

        venv/bin/python src/manage.py csv_import domains.csv 



## Requirements Handling

The project has automated handling of production requirements, the idea behind it is that
you should always use the latest versions of every requirement, a Makefile target is in place
to update the `requirements.txt` file (`make requirements.txt` will do).

In case you need a specific version of a library, the protocol should be:

* Place the needed fixed version using pip notation in any of the requirements/* files
* Put a comment over the fixed requirement explaining the reason for fixing it (usually with a link to an issue/bug)
* Run `make requirements.txt`, the resulting requirements file will include the fixed version of the package

For some more advanced uses, a manual edit of the requirements.txt can be done but make sure to document it somewhere because `make requirements.txt` *will* overwrite this file.



# Testing against latest versions

By default, `tox` and `make test` will only test against production requirements, in order to test against latest versions of the dependencies, there are two tox environments, `latest27` and `latest35`.

They can be run via `tox -e latest27,latest35` or also with `make test_latest`



## Contributing

Please go to [Main Zenaida GitHub repository](https://github.com/datahaven-net/zenaida), click "Fork", and clone your fork repository via git+ssh link:

        git clone git@github.com:< your GitHub username here >/zenaida.git


Then you need to add main Zenaida repo as "upstream" source via HTTPS link (in read-only mode):

        cd zenaida
        git remote add upstream https://github.com/datahaven-net/zenaida.git
        git remote -v
        origin  git@github.com:< your GitHub username here >/zenaida.git (fetch)
        origin  git@github.com:< your GitHub username here >/zenaida.git (push)
        upstream    https://github.com/datahaven-net/zenaida.git (fetch)
        upstream    https://github.com/datahaven-net/zenaida.git (push)


Your current forked repository remains as "origin", and you should always commiting and pushing to your own code base:

        # after you made some modifications, for example in README.md
        git add README.md
        git commit -m "updated documentation"
        git push origin master


Then you start a [new Pull Request](https://github.com/datahaven-net/zenaida/compare) towards main repository, you can click "compare across forks" link to select your own repository source in "head fork" drop down list. Then you will see the changes you are going to introduce to Zenaida and will be able to start a Pull Request.

Please cooperate with the open-source Zenaida community to make your changes Approved and Merged into the main repository. As soon as your Pull Request was merged, you can refresh your local files and "origin" repository:

        git pull upstream master
        git push origin master

