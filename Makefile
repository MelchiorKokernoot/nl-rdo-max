env = env PATH=${bin}:$$PATH

venv: .venv/touchfile ## Create virtual environment
.venv/touchfile:
	test -d .venv || python3 -m venv .venv
	. .venv/bin/activate; pip install -U pip
	. .venv/bin/activate; pip install pip-tools
	. .venv/bin/activate && ${env} python3 -m piptools compile requirements.in
	. .venv/bin/activate && ${env} python3 -m piptools compile requirements-dev.in
	. .venv/bin/activate && ${env} python3 -m piptools sync requirements.txt requirements-dev.txt
	. .venv/bin/activate && ${env} pip install -e .
	touch .venv/touchfile

clean_venv: ## Remove virtual environment
	@echo "Cleaning venv"
	@rm -rf .venv

clients.json: clients.json.example
	cp clients.json.example clients.json

inge6.conf: inge6.conf.example
	cp inge6.conf.example inge6.conf

saml/tvs/settings.json: saml/settings.json.example
	cp saml/settings.json.example saml/tvs/settings.json

saml/digid/settings.json: saml/settings.json.example
	cp saml/settings.json.example saml/digid/settings.json

secrets/private_unencrypted.pem:
	openssl genrsa -out secrets/private_unencrypted.pem 2048
secrets/public.pem: secrets/private_unencrypted.pem
	openssl rsa -in secrets/private_unencrypted.pem -pubout -out secrets/public.pem

saml/tvs/certs/sp.key:
	openssl genrsa -out saml/tvs/certs/sp.key 2048
saml/tvs/certs/sp.crt: saml/tvs/certs/sp.key
	openssl req -new -x509 -key saml/tvs/certs/sp.key -out saml/tvs/certs/sp.crt -days 360 -subj "/C=US/ST=SCA/L=SCA/O=Oracle/OU=Java/CN=test cert"

saml/digid/certs/sp.key:
	openssl genrsa -out saml/digid/certs/sp.key 2048
saml/digid/certs/sp.crt: saml/digid/certs/sp.key
	openssl req -new -x509 -key saml/digid/certs/sp.key -out saml/digid/certs/sp.crt -days 360 -subj "/C=US/ST=SCA/L=SCA/O=Oracle/OU=Java/CN=test cert"

setup: inge6.conf saml/tvs/settings.json secrets clients.json secrets/public.pem saml/tvs/certs/sp.crt saml/digid/certs/sp.crt

fresh: clean_venv venv

pip-compile: ## synchronizes the .venv with the state of requirements.txt
	. .venv/bin/activate && ${env} python3 -m piptools compile requirements.in
	. .venv/bin/activate && ${env} python3 -m piptools compile requirements-dev.in

pip-sync: ## synchronizes the .venv with the state of requirements.txt
	. .venv/bin/activate && ${env} python3 -m piptools sync requirements.txt
	. .venv/bin/activate && ${env} pip install -e .

pip-sync-dev: ## synchronizes the .venv with the state of requirements.txt
	. .venv/bin/activate && ${env} python3 -m piptools sync requirements.txt requirements-dev.txt
	. .venv/bin/activate && ${env} pip install -e .

lint:
	. .venv/bin/activate && ${env} pylint inge6 tests

audit:
	. .venv/bin/activate && ${env} bandit inge6

test:
	. .venv/bin/activate && ${env} pytest tests

type-check:
	. .venv/bin/activate && ${env} MYPYPATH=stubs/ mypy --show-error-codes inge6

check-all: lint type-check test audit
