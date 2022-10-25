env = env PATH="${bin}:$$PATH"
create_key_pair =

complete: venv secrets/ssl/private/apache-selfsigned.key secrets/oidc/private/selfsigned.key

venv: .venv/touchfile ## Create virtual environment
.venv/touchfile:
	test -d .venv || python3 -m venv .venv
	. .venv/bin/activate; pip install -U pip
	. .venv/bin/activate; pip install pip-tools
	. .venv/bin/activate && ${env} pip-compile --extra dev
	. .venv/bin/activate && ${env} pip-sync
	. .venv/bin/activate && ${env} pip install -e .
	touch .venv/touchfile

clean_venv: ## Remove virtual environment
	@echo "Cleaning venv"
	@rm -rf .venv

run:
	docker-compose stop && docker-compose up -d
	source .venv/bin/activate && python3 -m app.main

pip-sync: ## synchronizes the .venv with the state of requirements.txt
	. .venv/bin/activate && ${env} pip-compile --extra dev
	. .venv/bin/activate && ${env} pip-sync
	. .venv/bin/activate && ${env} pip install -e .

setup-secrets:
	scripts/./setup-secrets.sh

setup-saml:
	scripts/./setup-saml.sh

setup-config:
	scripts/./setup-config.sh

setup: setup-config setup-saml setup-secrets

lint:
	. .venv/bin/activate && ${env} pylint app tests
	. .venv/bin/activate && ${env} black --check inge6 tests

audit:
	. .venv/bin/activate && ${env} bandit inge6

fix:
	. .venv/bin/activate && $(env) black inge6 tests

test: venv setup
	. .venv/bin/activate && ${env} pytest tests

type-check:
	. .venv/bin/activate && ${env} MYPYPATH=stubs/ mypy --show-error-codes inge6

check-all: lint type-check test audit
