# This Makefile requires the following commands to be available:
# * virtualenv
# * python3.8
# * docker
# * docker-compose

REQUIREMENTS_BASE:=requirements/requirements-base.txt
REQUIREMENTS_TEST:=requirements/requirements-testing.txt
REQUIREMENTS_TXT:=requirements.txt

DOCKER_COMPOSE=$(shell which docker-compose)

PIP:="venv/bin/pip3"
TOX="venv/bin/tox"
PYTHON="venv/bin/python"
UWSGI="venv/bin/uwsgi"
EPPGATE="venv/bin/epp-gate"
TOX_PY_LIST="$(shell $(TOX) -l | grep ^py | xargs | sed -e 's/ /,/g')"
TOX_LATEST_LIST="latest38"

# Empty files used to keep track of installed types of virtualenvs (see rules below)
VENV_SYSTEM_SITE_PACKAGES=venv/.venv_system_site_packages
VENV_NO_SYSTEM_SITE_PACKAGES=venv/.venv_no_system_site_packages
VENV_DEPLOY=venv/.venv_deploy
VENV_BASE=venv/.venv_base
VENV_TEST=venv/.venv_test
VENV_TOX=venv/.venv_tox
VENV_DEV=venv/.venv_dev

# Params for building and installing on the EXA servers

VSN:=$(shell git describe --tags --always)
ARTIFACT:=zenaida-$(VSN).tgz
PIP_CACHE:=.pip_cache
PIP_DOWNLOAD:=.pip_download
PYTHON_VERSION=python3.8
BRANCH=$(shell git branch | grep '*' | awk '{print $$2}')
BUILD_PROPERTIES_FILE=build.properties
BUILD_PROPERTIES_JSONFILE=build.properties.json
MAKE_MIGRATIONS=`$(shell echo $(PYTHON)) src/manage.py makemigrations;`
MIGRATIONS_CHECK=`echo $(MAKE_MIGRATIONS_OUTPUT) | awk '{print match($$0, "No changes detected")}'`
PARAMS=src/main/params.py

.PHONY: clean docsclean pyclean test lint isort docs docker check_env \
	check_forgotten_migrations artifact \
	requirements_clean_virtualenv requirements_create_virtualenv requirements_build

tox: $(VENV_TOX)
	# tox
	PYTHONPATH=./src/ $(TOX)

# Used by the deploy pipeline to prepare for deploy
build: clean artifact

pyclean:
	# pyclean
	@find . -name *.pyc -delete
	@rm -rf *.egg-info build
	@rm -rf coverage.xml .coverage
	@rm -f zenaida-*.tgz

docsclean:
	@rm -fr docs/_build/

clean: pyclean docsclean
	# clean
	@rm -rf venv
	@rm -rf .tox

# Used by the deploy pipeline to get information about the artifact
# created by the build step.
properties:
	@echo "{\"artifact\": \"$(ARTIFACT)\", \"version\": \"$(VSN)\"}"

$(PARAMS): | src/main/params_example.py
	# PARAMS
	@cp $| $@

venv: $(VENV_DEV) $(PARAMS)
	# venv


check_forgotten_migrations: $(PARAMS) $(VENV_BASE)
	# check_forgotten_migrations
	$(eval MAKE_MIGRATIONS_OUTPUT:="$(shell echo $(MAKE_MIGRATIONS))")
	@echo $(MAKE_MIGRATIONS_OUTPUT)
	@if [ $(MIGRATIONS_CHECK) -gt 0 ]; then \
		echo "There aren't any forgotten migrations. Well done!"; \
	else \
		echo "Error! You've forgotten to add the migrations!"; \
		exit 1; \
	fi


check_requirements_txt:
	# check_requirements_txt
	@if [ ! -f "$(REQUIREMENTS_TXT)" ]; then \
		echo "ERROR: Missing $(REQUIREMENTS_TXT), it should be committed to the repository"; \
		exit 1; \
	fi
	@touch $(REQUIREMENTS_TXT) # to make sure that REQUIREMENTS_TXT is the requirements file with the latest timestamp


sanity_checks: check_requirements_txt check_forgotten_migrations
	@echo "Checks OK"


# Used by the PR jobs. This target should include all tests necessary
# to determine if the PR should be rejected or not.
#
# To run tests locally: use 'make test/path/to/test' for a selection
# or 'tox -e py35' to run test for only python35. Of course it's still
# possible to run 'pytest path/to/test'.
test: clean sanity_checks tox
	# test

test_latest: sanity_checks pyclean venv
	# test_latest
	$(TOX) -e $(TOX_LATEST_LIST) -- $*

test_dev: sanity_checks pyclean venv
	# test_dev
	$(TOX) -e dev -- $*

test/%: sanity_checks pyclean venv
	$(TOX) -e $(TOX_PY_LIST) -- $*

test_e2e: $(VENV_TOX)
	E2E=1 PYTHONPATH=./src .tox/py38/bin/py.test -v -s --capture=no src/tests/

lint: $(VENV_TOX)
	@$(TOX) -e lint
	@$(TOX) -e isort-check

isort: $(VENV_TOX)
	@$(TOX) -e isort-fix

docs: clean $(VENV_TOX) $(PARAMS)
	# @$(TOX) -e docs

docker/test:
	# docker/test
	$(DOCKER_COMPOSE) build && trap '$(DOCKER_COMPOSE) down' EXIT && $(DOCKER_COMPOSE) up --exit-code-from test --no-build

artifact: $(VENV_NO_SYSTEM_SITE_PACKAGES)
	# artifact
	@rm -rf .pip_download
	@echo "$(BRANCH) $(VSN)" > REVISION
	@tar -czf $(ARTIFACT) --exclude-from=.artifact_exclude * $(PIP_DOWNLOAD)
	@echo "version = $(VSN)" > $(BUILD_PROPERTIES_FILE)
	@echo "branch = $(BRANCH)" >> $(BUILD_PROPERTIES_FILE)
	@echo "artifact = $(ARTIFACT)" >> $(BUILD_PROPERTIES_FILE)
	@echo "{\"artifact\": \"$(ARTIFACT)\", \"version\": \"$(VSN)\", \"branch\": \"$(BRANCH)\"}" > $(BUILD_PROPERTIES_JSONFILE)
	@echo 'Done!'

check_env:
ifndef ENV
	$(error ENV is undefined)
endif

# Used by the deploy pipeline to finish installation after the artifact is extracted
install: check_env $(VENV_DEPLOY)
	@echo "ENV = '$(ENV)'" > $(PARAMS)
	@$(PYTHON) src/manage.py compilemessages
	@$(PYTHON) src/manage.py collectstatic --noinput
	@echo 'Done!'

# Used by the deploy pipeline to test if the software is working correctly
# This is called once after deployment to test and once after deployment to
# acceptance.
smoketest:
	@echo "No smoketest defined"
	/bin/false


runuwsgi: $(VENV_DEPLOY)
	$(UWSGI) --ini etc/local.uwsgi.ini


runserver: $(VENV_DEPLOY)
	SERVER_PROTOCOL="HTTP/1.1" $(PYTHON) src/manage.py runserver


createsuperuser: $(VENV_DEPLOY)
	$(PYTHON) src/manage.py createsuperuser
	@echo 'createsuperuser OK'


collectstatic: $(VENV_DEPLOY)
	$(PYTHON) src/manage.py collectstatic --noinput
	@echo 'collectstatic OK'


migrate: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py migrate --noinput
	@echo 'migrate OK'


makemigrations: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py makemigrations
	@echo 'makemigrations OK'


shell: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py shell


dbshell: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py dbshell


show_urls: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py show_urls


shell_plus: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py shell_plus


todo: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py notes


graph_models: $(VENV_DEPLOY)
	@$(PIP) install --upgrade pygraphviz
	@$(PYTHON) src/manage.py graph_models -a -g -o graph_models.png
	@$(PIP) uninstall --yes pygraphviz
	@echo 'File graph_models.png created.'


epp_gate_dev: $(VENV_DEPLOY)
	@echo "Starting epp gate with local credentials"
	@$(EPPGATE) --verbose --reconnect --epp=./keys.local/epp_credentials.txt --rabbitmq=./keys.local/rabbitmq_gate_credentials.txt --queue=epp_rpc_messages


epp_poll_dev: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py epp_poll


rabbitmq_server_dev:
	@echo "Starting RabbitMQ server, admin dashboard is avaialble here: http://127.0.0.1:15672"
	@rabbitmq-server


run_background_worker_dev: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py background_worker


run_process_notifications_dev: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py process_notifications


################################################
# Setting up of different kinds of virtualenvs #
################################################

$(REQUIREMENTS_TXT): $(VENV_NO_SYSTEM_SITE_PACKAGES)
	# REQUIREMENTS_TXT
	@$(PIP) install --upgrade pip
	@$(PIP) install -r $(REQUIREMENTS_BASE)
	@rm -vf $(REQUIREMENTS_TXT)
	@$(PIP) freeze > $(REQUIREMENTS_TXT)
	@sed -i -E "s/epp-python-client==.+//" $(REQUIREMENTS_TXT)
	@echo "https://github.com/datahaven-net/epp-python-client/archive/master.zip" >> $(REQUIREMENTS_TXT)
	@echo "Successfully Updated requirements.txt"

# these two are the main venvs
$(VENV_SYSTEM_SITE_PACKAGES):
	# VENV_SYSTEM_SITE_PACKAGES
	@rm -rf venv
	@$(PYTHON_VERSION) -m venv --system-site-packages venv
	@echo "[easy_install]" > venv/.pydistutils.cfg
	@echo "find_links = file://$(PWD)/$(PIP_DOWNLOAD)/" >> venv/.pydistutils.cfg
	@touch $@

$(VENV_NO_SYSTEM_SITE_PACKAGES):
	# VENV_NO_SYSTEM_SITE_PACKAGES
	@rm -rf venv
	@$(PYTHON_VERSION) -m venv venv
	@touch $@

# the rest is based on main venvs
$(VENV_DEPLOY): $(VENV_NO_SYSTEM_SITE_PACKAGES) check_requirements_txt
	# VENV_DEPLOY
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r $(REQUIREMENTS_TXT)
	@touch $@

$(VENV_BASE): $(VENV_NO_SYSTEM_SITE_PACKAGES) check_requirements_txt
	# VENV_BASE
	@$(PIP) install --upgrade pip
	@$(PIP) install -r $(REQUIREMENTS_TXT)
	@touch $@

$(VENV_TEST): $(VENV_NO_SYSTEM_SITE_PACKAGES) $(REQUIREMENTS_TEST)
	# VENV_TEST
	@$(PIP) install --upgrade pip
	@$(PIP) install -r $(REQUIREMENTS_TEST)
	@touch $@

$(VENV_TOX): $(VENV_NO_SYSTEM_SITE_PACKAGES)
	# VENV_TOX
	@$(PIP) install --upgrade pip
	@$(PIP) install tox importlib.metadata==2.0.0
	@touch $@

$(VENV_DEV): $(VENV_TOX) $(VENV_BASE) $(VENV_TEST)
	# VENV_DEV
	@$(PIP) install pytest
	@touch $@
