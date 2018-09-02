# Zenaida

Open source domain registry system built on top of EPP protocol



## Get Started

Clone project files locally. If you are running on production server please use user `zenaida` and run all applications on behalf of that user:

        sudo adduser zenaida
        sudo usermod -aG sudo zenaida
        sudo su zenaida
        cd ~
        git clone https://github.com/datahaven-net/zenaida.git
        cd zenaida


Install postgress and few other packages:

        sudo apt-get install make python3-pip python3-dev python3-venv libpq-dev postgresql postgresql-contrib

 
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


To be abe to run same code on production machine as well as locally on your laptop you can use isolated development settings, configure this by setting `src/main/params.py` file:

        cp src/main/params.example.py src/main/params.py
        nano src/main/params.py


Set those settings in your `params.py` file if you starting a new production machine:

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

You might want to use your own tweaks for nginx and uwsgi, so those files are just a starting point.

Make sure you set the correct domain name on your server:

        sudo hostname -b yourdomain.com


Install nginx if you do not have it yet installed and update the configuration:
        
        sudo apt-get install nginx
        sudo cp etc/nginx/zenaida /etc/nginx/sites-available/zenaida
        sudo ln -s /etc/nginx/sites-available/zenaida /etc/nginx/sites-enabled/
        sudo unlink /etc/nginx/sites-enabled/default


Lets configure uwsgi in emperor mode to follow best practices. We will need one vassal to be running and serving Zenaida traffic:


Also copy configuration for zenaida uwsgi process to global init scripts:

        sudo cp etc/uwsgi-zenaida.conf /etc/init.d/uwsgi-zenaida


Restart uwsgi service for zenaida:

        sudo stop uwsgi-zenaida
        sudo start uwsgi-zenaida


You can always check current situation with:

        sudo initctl status uwsgi-zenaida


Finally create separate folder to store server logs and restart nginx server:

        mkdir /home/zenaida/logs/
        sudo chgrp www-data /home/zenaida/logs/
        sudo service nginx restart


Your live server should be up and running now, navigate your browser to http://www.yourdomain.com



## Install Perl and required modules

To establish connection between Zenaida server and EPP registry system we use couple more components:

* RabbitMQ server to run messaging queue and exchange EPP commands
* Perl script which runs in background and keep alive connection with EPP server
* Python Polling job which periodically request updates from EPP server for backward synchronization   


Lets start from installing Perl and required modules on Zenaida machine.
Few binary dependencies are required to running Perl modules:

        sudo apt-get install build-essential libxml2-dev libnet-ssleay-perl libssl-dev libdigest-sha1-perl 


Then we need to check if CPAN Perl package manager is installed and configured on your OS - it should be present on most Linux systems by default after installing `build-essential` package:

        cpan


Installing Perl modules is easy, but takes some time:

        sudo cpan install AnyEvent TryCatch JSON XML::LibXML Method::Signatures Digest::MD5 Data::Dumper HTTP::Daemon  Net::RabbitFoot Net::Server::PreFork Net::EPP::Simple



## Install and configure RabbitMQ

RabbitMQ is used to drive a EPP messaging queue between Zenaida host and EPP registry system.

Use Apt package manager to install RabbitMQ server on your Zenaida host:

        echo "deb https://www.rabbitmq.com/debian testing main" | sudo tee /etc/apt/sources.list.d/rabbitmq.list
        wget -O- https://www.rabbitmq.com/rabbitmq-release-signing-key.asc | sudo apt-key add -
        sudo apt-get update
        sudo apt-get install rabbitmq-server
        sudo rabbitmq-plugins enable rabbitmq_management
        sudo rabbitmqctl add_user zenaida-admin <rabbitmq password>
        sudo rabbitmqctl set_user_tags zenaida administrator
        sudo rabbitmqctl set_permissions -p / zenaida ".*" ".*" ".*"


Now you can navigate your web browser to RabbitMQ dashboard at `http://www.yourdomain.com:15672` and login with `zenaida-admin`:`<rabbitmq password>` credentials you have just created.

Now it is time to create live RabbitMQ credentials to access messaging queue. Got to `http://www.yourdomain.com:15672/#/users`, click "Add user" dropdown link, set username and password fields and click "Add user" button. Then select that user and click "Set permission" button to grant him access to virtual hosts.

More details about RabbutMQ installation you can find here: https://www.rabbitmq.com/install-debian.html


## Establish connection with EPP registry

To run real-time connection between Zenaida and EPP registry system a separate process was developed which is called "EPP Gate". You will find this Perl script in `bin/epp_gate.pl` file.

To be able to start EPP Gate process you need to provide it with required credentials for EPP registry and RabbitMQ - example files you can find in `etc/` folder. You can place those files in a safe place on your server and fill with correct credentials:

        mkdir /home/zenaida/keys/
        echo "localhost 5672 <rabbitmq_user> <rabbitmq_password>" > /home/zenaida/keys/rabbitmq_gate_credentials.txt
        echo "epp.yourdomain.com 700 <epp_user> <epp_password>" > /home/zenaida/keys/epp_credentials.txt
        chmod go-rwx -R /home/zenaida/keys/


Next create a folder to store log files:

        mkdir /home/zenaida/logs/
        chmod go-rwx -R /home/zenaida/logs/


Now we need to be sure that "EPP Gate" process is configured correctly, lets execute Perl script directly:

        perl proc/epp_gate.pl /home/zenaida/keys/epp_credentials.txt /home/zenaida/keys/rabbitmq_gate_credentials.txt
        ...
        Sat May 19 20:49:17 2018: Connecting to RabbitMQ server at localhost:5672 with username: <rabbitmq_user>
        Sat May 19 20:49:17 2018:  [x] Awaiting RPC requests


Keep it running in the current terminal and open another console window to be able to fire real-time EPP requests towards given EPP server:

        venv/bin/python -c 'import sys; sys.path.append("src/"); import zepp.client; print(zepp.client.cmd_domain_check(["testdomain.com", ]))'


If RabbitMQ and EPP Gate process was configured correctly you should see a json response from EPP Gate like that:

        {'epp': {'@{http://www.w3.org/2001/XMLSchema-instance}schemaLocation': 'urn:ietf:params:xml:ns:epp-1.0 epp-1.0.xsd', 'response': {'result': {'@code': '1000', 'msg': 'Command completed successfully'}, 'resData': {'chkData': {'@{http://www.w3.org/2001/XMLSchema-instance}schemaLocation': 'urn:ietf:params:xml:ns:domain-1.0 domain-1.0.xsd', 'cd': {'name': {'@avail': '1', '#text': 'testdomain.com'}}}}, 'trID': {'clTRID': '103513f75a176e56038b2244258357f7', 'svTRID': '1526756418267'}}}}
      

To be able to easily manage EPP Gate process on your host system you can add it to your system-wide init scripts:

        sudo cp etc/gate-zenaida.conf /etc/init/gate-zenaida.conf


Then you can stop/start EPP Gate service this way:

        sudo stop gate-zenaida
        sudo start gate-zenaida


You can always check current situation with:

        sudo initctl status gate-zenaida 



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

