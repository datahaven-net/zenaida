# This Makefile requires the following commands to be available:
# * virtualenv
# * python3.6
# * docker
# * docker-compose

REQUIREMENTS_BASE:=requirements/requirements-base.txt
REQUIREMENTS_TEST:=requirements/requirements-testing.txt
REQUIREMENTS_TXT:=requirements.txt

DOCKER_COMPOSE=$(shell which docker-compose)

PIP:="venv/bin/pip"
TOX="venv/bin/tox"
PYTHON="venv/bin/python"
TOX_PY_LIST="$(shell $(TOX) -l | grep ^py | xargs | sed -e 's/ /,/g')"
TOX_LATEST_LIST="latest36"

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
ARTIFACT:=zenaida1-$(VSN).tgz
PIP_CACHE:=.pip_cache
PIP_DOWNLOAD:=.pip_download
PYTHON_VERSION=python3.6
BRANCH=$(shell git branch | grep '*' | awk '{print $$2}')
BUILD_PROPERTIES_FILE=build.properties
BUILD_PROPERTIES_JSONFILE=build.properties.json
MAKE_MIGRATIONS=`$(shell echo $(PYTHON)) src/manage.py makemigrations;`
MIGRATIONS_CHECK=`echo $(MAKE_MIGRATIONS_OUTPUT) | awk '{print match($$0, "No changes detected")}'`
PARAMS=src/main/params.py

.PHONY: clean docsclean pyclean test lint isort docs docker setup.py check_env \
	check_forgotten_migrations artifact \
	requirements_clean_virtualenv requirements_create_virtualenv requirements_build

tox: $(VENV_TOX) setup.py
	$(TOX)

# Used by the deploy pipeline to prepare for deploy
build: clean artifact

pyclean:
	@find . -name *.pyc -delete
	@rm -rf *.egg-info build
	@rm -rf coverage.xml .coverage
	@rm -f zenaida1-*.tgz

docsclean:
	@rm -fr docs/_build/

clean: pyclean docsclean
	@rm -rf venv
	@rm -rf .tox

# Used by the deploy pipeline to get information about the artifact
# created by the build step.
properties:
	@echo "{\"artifact\": \"$(ARTIFACT)\", \"version\": \"$(VSN)\"}"

$(PARAMS): | src/main/params.example.py
	@cp $| $@

venv: $(VENV_DEV) $(PARAMS)

check_forgotten_migrations: $(PARAMS) $(VENV_BASE)
	$(eval MAKE_MIGRATIONS_OUTPUT:="$(shell echo $(MAKE_MIGRATIONS))")
	@echo $(MAKE_MIGRATIONS_OUTPUT)
	@if [ $(MIGRATIONS_CHECK) -gt 0 ]; then \
		echo "There aren't any forgotten migrations. Well done!"; \
	else \
		echo "Error! You've forgotten to add the migrations!"; \
		exit 1; \
	fi


check_requirements_txt:
	@if [ ! -f "$(REQUIREMENTS_TXT)" ]; then \
		echo "ERROR: Missing $(REQUIREMENTS_TXT), it should be committed to the repository"; \
		exit 1; \
	fi
	@touch $(REQUIREMENTS_TXT) # to make sure that REQUIREMENTS_TXT is the requirements file with the latest timestamp

sanity_checks: check_requirements_txt check_forgotten_migrations
	@echo "Checks OK"

# Used by the deploy pipeline to do migrations that only have to run
# on one node only, not all nodes where the software is installed.
migrate: $(VENV_DEPLOY)
	@$(PYTHON) src/manage.py migrate --noinput
	@echo 'Done!'


# Used by the PR jobs. This target should include all tests necessary
# to determine if the PR should be rejected or not.
#
# To run tests locally: use 'make test/path/to/test' for a selection
# or 'tox -e py35' to run test for only python35. Of course it's still
# possible to run 'pytest path/to/test'.
test: clean sanity_checks tox

test_latest: sanity_checks pyclean venv
	$(TOX) -e $(TOX_LATEST_LIST) -- $*

test_dev: sanity_checks pyclean venv
	$(TOX) -e dev -- $*

test/%: sanity_checks pyclean venv
	$(TOX) -e $(TOX_PY_LIST) -- $*

lint: $(VENV_TOX)
	@$(TOX) -e lint
	@$(TOX) -e isort-check

isort: $(VENV_TOX)
	@$(TOX) -e isort-fix

docs: clean $(VENV_TOX) $(PARAMS)
	@$(TOX) -e docs

# TODO maybe run via uwsgi?
docker:
	$(DOCKER_COMPOSE) run --rm app bash

docker/%:
	$(DOCKER_COMPOSE) run --rm app make $*

setup.py: $(VENV_DEV)
	$(PYTHON) setup_gen.py

artifact: $(VENV_NO_SYSTEM_SITE_PACKAGES)
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


runserver: $(VENV_DEV)
	$(PYTHON) src/manage.py runserver


$(REQUIREMENTS_TXT): $(REQUIREMENTS_BASE) | $(VENV_TOX)
	@$(TOX) -e requirements_txt
	@echo "Successfully Updated requirements"


################################################
# Setting up of different kinds of virtualenvs #
################################################

# these two are the main venvs
$(VENV_SYSTEM_SITE_PACKAGES):
	@rm -rf venv
	@$(PYTHON_VERSION) -m venv --system-site-packages venv
	@echo "[easy_install]" > venv/.pydistutils.cfg
	@echo "find_links = file://$(PWD)/$(PIP_DOWNLOAD)/" >> venv/.pydistutils.cfg
	@touch $@

$(VENV_NO_SYSTEM_SITE_PACKAGES):
	@rm -rf venv
	@$(PYTHON_VERSION) -m venv venv
	@touch $@

# the rest is based on main venvs
$(VENV_DEPLOY): $(VENV_SYSTEM_SITE_PACKAGES) check_requirements_txt
	@touch $@

$(VENV_BASE): $(VENV_NO_SYSTEM_SITE_PACKAGES) check_requirements_txt
	@$(PIP) install -r $(REQUIREMENTS_TXT)
	@touch $@

$(VENV_TEST): $(VENV_NO_SYSTEM_SITE_PACKAGES) $(REQUIREMENTS_TEST)
	@$(PIP) install -r $(REQUIREMENTS_TEST)
	@touch $@

$(VENV_TOX): $(VENV_NO_SYSTEM_SITE_PACKAGES)
	@$(PIP) install tox
	@touch $@

$(VENV_DEV): $(VENV_TOX) $(VENV_BASE) $(VENV_TEST)
	@touch $@
