import json
from typing import Tuple

from functools import cached_property

from packaging.version import Version
from packaging.version import parse as version_parse

from inge6.saml.saml_request import ArtifactResolveRequest, AuthNRequest

from .metadata import IdPMetadata, SPMetadata
from .utils import from_settings

# pylint: disable=too-many-instance-attributes
class IdProvider:

    def __init__(self, name, idp_setting, jinja_env) -> None:
        self.name = name
        self.saml_spec_version = version_parse(str(idp_setting['saml_specification_version']))
        self.base_dir = idp_setting['base_dir']
        self.cert_path = idp_setting['cert_path']
        self.key_path = idp_setting['key_path']
        self.settings_path = idp_setting['settings_path']
        self.advanced_settings_path = idp_setting['advanced_settings_path']
        self.idp_metadata_path = idp_setting['idp_metadata_path']

        self.jinja_env = jinja_env

        with open(self.settings_path, 'r', encoding='utf-8') as settings_file:
            self.settings_dict = json.loads(settings_file.read())

        with open(self.advanced_settings_path, 'r', encoding='utf-8') as adv_settings_file:
            self.settings_dict.update(json.loads(adv_settings_file.read()))

        with open(self.key_path, 'r', encoding='utf-8') as key_file:
            self.priv_key = key_file.read()

        self._idp_metadata = IdPMetadata(self.idp_metadata_path)
        self._sp_metadata = SPMetadata(self.settings_dict, self.keypair_paths, self.jinja_env)

    @cached_property
    def authn_binding(self):
        return from_settings(self.settings_dict, 'idp.singleSignOnService.binding')

    @property
    def keypair_paths(self) -> Tuple[str, str]:
        return (self.cert_path, self.key_path)

    @property
    def sp_metadata(self) -> SPMetadata:
        return self._sp_metadata

    @property
    def idp_metadata(self) -> IdPMetadata:
        return self._idp_metadata

    @property
    def saml_is_new_version(self):
        return self.saml_spec_version >= Version("4.4")

    @property
    def saml_is_legacy_version(self):
        return self.saml_spec_version == Version("3.5")

    def create_authn_request(self, cluster_name = None, machtigen=False):
        sso_url = self.idp_metadata.get_sso()['location']

        if machtigen:
            return AuthNRequest(sso_url, self.sp_metadata, self.jinja_env, scoping_list=[
                "urn:nl-eid-gdi:1.0:AD:00000004166909913000:entities:0001",
                "urn:nl-eid-gdi:1.0:BVD:00000004003214345001:entities:0001"
            ],
            request_ids=[
                "urn:nl-eid-gdi:1.0:BVD:00000004003214345001:entities:0001"
            ],
            cluster_name=cluster_name
        )
        return AuthNRequest(sso_url, self.sp_metadata, self.jinja_env, scoping_list=[
                "urn:nl-eid-gdi:1.0:AD:00000004166909913000:entities:0001",
            ],
            cluster_name=cluster_name
        )

    def create_artifactresolve_request(self, artifact: str):
        sso_url = self.idp_metadata.get_sso()['location']
        return ArtifactResolveRequest(artifact, sso_url, self.sp_metadata, self.jinja_env)
