-include .env

ENV_CONF = -f docker-compose.yml

ifeq (${ENV},prod)
#	ENV_CONF = -f docker-compose.yml -f docker-compose.logging.yml -f docker-compose.prod.yml
	ENV_CONF = -f docker-compose.yml -f docker-compose.dev.yml
endif

ifeq (${ENV},dev)
#	ENV_CONF = -f docker-compose.yml -f docker-compose.logging.yml -f docker-compose.prod.yml
	ENV_CONF = -f docker-compose.yml -f docker-compose.dev.yml
endif

ifeq (${ENV},local)
	ENV_CONF = -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.local.yml
endif

ifeq (${PROFILE},development)
	ENV_CONF += --profile development
endif

ifeq (${PROFILE},main)
	ENV_CONF += --profile main
endif

SRC_DIR=src
BACKUPS_DIR=.backups

LOCALE_DIR=$(SRC_DIR)/locale
LOCALE_CONFIG=$(LOCALE_DIR)/babel.cfg
MESSAGE_DOMAIN=messages
MESSAGE_DOMAIN_FILE=$(LOCALE_DIR)/$(MESSAGE_DOMAIN).pot

RUNNER=uv run

env ?= "local"
path ?= "none"

##################
## Localization ##
##################

locale-init:
	$(RUNNER) pybabel init --output-dir=$(LOCALE_DIR) --locale=$(locale) --no-wrap

locale-new:
	$(RUNNER) pybabel init --input-file=$(MESSAGE_DOMAIN_FILE) --output-dir=$(LOCALE_DIR) --locale=$(locale) --no-wrap

locale-compile:
	$(RUNNER) pybabel compile --domain=$(MESSAGE_DOMAIN) --use-fuzzy --directory=$(LOCALE_DIR)

locale-update:
	$(RUNNER) pybabel update --domain=$(MESSAGE_DOMAIN) --input-file=$(MESSAGE_DOMAIN_FILE) --output-dir=$(LOCALE_DIR) --no-wrap

locale-template:
	$(RUNNER) pybabel extract --mapping-file=$(LOCALE_CONFIG) --output-file=$(MESSAGE_DOMAIN_FILE) --no-wrap .

#############
## Ansible ##
#############

encrypt:
	ansible-vault encrypt ansible/group_vars/*/vault.yml

decrypt:
	ansible-vault decrypt ansible/group_vars/*/vault.yml

backup:
	[ -d $(BACKUPS_DIR) ] || mkdir $(BACKUPS_DIR) || echo "Created missing backup directory.";
	ansible-playbook \
 		--extra-vars="env=$(env)$(if $(dump_name), dump_name=$(dump_name))" \
 		 ansible/backup.yml

last_backup := $(shell ls -A .backups | tail -1)
ifeq ($(path),"none")
    dump_file=$(last_backup)
else
    dump_file=$(path)
endif
restore:
	[ -d $(BACKUPS_DIR) ] || mkdir $(BACKUPS_DIR) || echo "Created missing backup directory.";
	ansible-playbook \
 		--extra-vars="dump_path=\"$(dump_file)\" env=$(env)" \
 		 ansible/restore.yml;

############
## Docker ##
############

pull:
	docker compose $(ENV_CONF) pull

push:
	docker compose $(ENV_CONF) push

build:
	docker compose $(ENV_CONF) build

up:
	docker compose $(ENV_CONF) up --detach --remove-orphans

restart:
	docker compose $(ENV_CONF) restart

down:
	docker compose $(ENV_CONF) down

clear-cache:
	docker compose $(ENV_CONF) run --rm redis redis-cli -h localhost -p ${REDIS_PORT} -n ${REDIS_CACHE_DB} FLUSHDB

##########################
## Linters & Formatters ##
##########################

mypy:
	$(RUNNER) mypy --config formatters-cfg.toml $(SRC_DIR)

flake:
	$(RUNNER) flake8 --toml-config formatters-cfg.toml $(SRC_DIR)

black:
	$(RUNNER) black --config formatters-cfg.toml $(SRC_DIR)

black-lint:
	$(RUNNER) black --check --config formatters-cfg.toml $(SRC_DIR)

isort:
	$(RUNNER) isort --settings-path formatters-cfg.toml $(SRC_DIR)

format: black isort

lint: flake mypy black-lint

###########
## Tests ##
###########

test:
	$(RUNNER) pytest --junitxml=backend-test-report.xml --cov --cov-report term --cov-report xml:coverage.xml --test-alembic -n 2 --reruns 3 $(SRC_DIR)

################
## Migrations ##
################

migrate:
	$(RUNNER) alembic upgrade head

migrate-ci:
	docker compose $(ENV_CONF) run --rm api alembic upgrade head

revert-migrate:
	$(RUNNER) alembic downgrade -1

makemigrations:
	$(RUNNER) alembic revision --autogenerate -m "$(message)"
