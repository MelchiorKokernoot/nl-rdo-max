import json

from jwkest.jwk import RSAKey, rsa_load

from pyop.storage import RedisWrapper
from pyop.authz_state import AuthorizationState
from pyop.provider import Provider as PyopProvider
from pyop.subject_identifier import HashBasedSubjectIdentifierFactory
from pyop.userinfo import Userinfo

from ..config import settings
from ..cache import get_redis_client

class Provider:

    def __init__(self, app):
        issuer = settings.issuer
        authentication_endpoint = app.url_path_for('authorize')
        jwks_uri = app.url_path_for('jwks_uri')
        token_endpoint = app.url_path_for('token_endpoint')

        configuration_information = {
            'issuer': issuer,
            'authorization_endpoint': issuer + authentication_endpoint,
            'jwks_uri': issuer + jwks_uri,
            'token_endpoint': issuer + token_endpoint,
            'scopes_supported': ['openid', 'profile'],
            'response_types_supported': ['code', 'code id_token', 'code token', 'code id_token token'],  # code and hybrid
            'response_modes_supported': ['query', 'fragment'],
            'grant_types_supported': ['authorization_code', 'implicit'],
            'subject_types_supported': ['pairwise'],
            'token_endpoint_auth_methods_supported': ['none'],
            'claims_parameter_supported': True
        }

        userinfo_db = Userinfo({'test_client': {'name': 'test_client'}})
        with open(settings.oidc.clients_file) as clients_file:
            clients = json.load(clients_file)

        signing_key = RSAKey(key=rsa_load(settings.oidc.rsa_private_key), alg='RS256', )

        authorization_code_db = RedisWrapper(collection=settings.redis.code_namespace, redis=get_redis_client())
        access_token_db = RedisWrapper(collection=settings.redis.token_namespace, redis=get_redis_client())
        refresh_token_db = RedisWrapper(collection=settings.redis.refresh_token_namespace, redis=get_redis_client())
        subject_identifier_db = RedisWrapper(collection=settings.redis.sub_id_namespace, redis=get_redis_client())

        authz_state = AuthorizationState(
            HashBasedSubjectIdentifierFactory(settings.oidc.subject_id_hash_salt),
            authorization_code_db=authorization_code_db,
            access_token_db=access_token_db,
            refresh_token_db=refresh_token_db,
            subject_identifier_db=subject_identifier_db
        )

        self.provider = PyopProvider(signing_key, configuration_information,
                            authz_state,
                            clients, userinfo_db)

    def __getattr__(self, name):
        if hasattr(self.provider, name):
            return getattr(self.provider, name)

        raise AttributeError("Attribute {} not found".format(name))

