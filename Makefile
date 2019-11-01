export SHELL  := /bin/bash

.DEFAULT_GOAL := usage

BOLD   := \033[1m
BRED   := \033[1;31m
RED    := \033[0;31m
GREEN  := \033[0;32m
CYAN   := \033[0;36m
BLUE   := \033[0;34m
BBLUE  := \033[1;34m
YELLOW := \033[0;33m
LGRAY  := \033[0;37m
DGRAY  := \033[0;90m
NC     := \033[0m

usage:
	@printf "\n$(BOLD)Usage:$(NC)\n\n"
	@printf "  make patch             $(GREEN)# Bump minor version and push upstream (no releases) $(NC)\n"
	@printf "  make test              $(GREEN)# Build and test the package $(NC)\n"
	@printf "  make release           $(GREEN)# Build and push a release $(NC)\n"
	@printf "  make devrelease        $(GREEN)# Build and push a developer release $(NC)\n"
	@printf "$(BOLD)Options:$(NC)\n\n"
	@printf "  KEYCLOAK_VERSION       provide the version of Keycloak used for testing (e.g. $(KEYCLOAK_VERSION))\n\n"
	@exit 1

# ---- defaults and macros -----------------------------------------------------

# set the branch to patch after release tagging
BRANCH ?= develop

# the version macro is used for tagging the builds in git
# BEWARE: this macro expands at the start when the make file is run, if you do something
#         to the version file, this variable will be set to the old version !!!
VERSION ?= $(shell cat .bumpversion.cfg | grep current_version | awk '{ print $$3 }')

# python installs into local user bin which is not on our path
export PATH := ./venv/bin:$(PATH)

# ---- build and release  ------------------------------------------------------

export PYPI_REPOSITORY_URL ?= https://pypi.org/

.PHONY: clean
clean:
	@rm -rf dist build .pytest_cache tests/__pycache__ *.egg-info venv

# includes dirty hack to remove pip leaky passwords
venv/bin/activate: requirements.txt
	@test -d venv || virtualenv venv --python=$(shell which python3)
	@venv/bin/pip install -Ur requirements.txt | sed 's|https:\/\/.*@|https:\/\/|g'
	@touch venv/bin/activate

venv: venv/bin/activate

.PHONY: build
build: clean venv
	@python setup.py sdist bdist_wheel

.PHONY: release
release: build
ifdef GPG_KEY
	@gpg --detach-sign -a --default-key $GPG_KEY dist/jyboss-$(VERSION).tar.gz
	@gpg --detach-sign -a --default-key $GPG_KEY dist/jyboss-$(VERSION)-py2.py3-none-any.whl
	@source venv/bin/activate && \
   twine upload --repository-url "$(PYPI_REPOSITORY_URL)" \
                            dist/jyboss-$(VERSION).tar.gz \
                            dist/jyboss-$(VERSION).tar.gz.asc \
                            dist/jyboss-$(VERSION)-py2.py3-none-any.whl \
                            dist/jyboss-$(VERSION)-py2.py3-none-any.whl.asc
endif

.PHONY: devrelease
devrelease:
	$(MAKE) release PYPI_REPOSITORY_URL=https://test.pypi.org/legacy/

# ---- TODO development and testing  -------------------------------------------

export KEYCLOAK_VERSION ?= 4.8.3.Final
export JBOSS_HOME ?= ./tmp/server
export JYTHON_HOME ?= /usr/local/opt/jython

JYTHON_COMMAND = $(shell command -v jython 2> /dev/null)

.PHONY: init
init:
	$(info install test server $(KEYCLOAK_VERSION))
ifndef JYTHON_HOME
	$(error JYTHON_HOME must point to a valid jython command)
endif
ifndef JYTHON_COMMAND
	$(error jython executable is not on the path)
endif

devbuild: # depends jyenv
	@jyenv/bin/pip install -U --editable . | sed 's|https:\/\/.*@|https:\/\/|g'

.PHONY: test
test: init
# TODO setup JBoss environment for testing
	@PATH=$(JYTHON_HOME)/bin:$$PATH nosetests --verbose
