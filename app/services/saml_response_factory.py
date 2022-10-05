import base64
import json
import logging
import os

from jinja2 import Template

from starlette.background import BackgroundTask
from starlette.responses import HTMLResponse, RedirectResponse

from app.exceptions.max_exceptions import AuthorizationByProxyDisabled, UnexpectedAuthnBinding
from app.models.saml.exceptions import ScopingAttributesNotAllowed
from app.models.saml.saml_request import AuthNRequest
from onelogin.saml2.auth import OneLogin_Saml2_Auth

log = logging.getLogger(__package__)


class SAMLResponseFactory():
    def __init__(
            self,
            html_templates_path: str,
            saml_base_issuer: str,
            oidc_authorize_endpoint: str
    ):
        self._saml_base_issuer = saml_base_issuer
        self._oidc_authorize_endpoint = oidc_authorize_endpoint

        template_path = os.path.join(html_templates_path, "authn_request.html")
        with open(template_path, "r", encoding="utf-8") as template_file:
            self._template_txt = template_file.read()

    def create_saml_response(self, mock_digid, saml_identity_provider, login_digid_request, randstate):
        if mock_digid:
            return self._create_digid_mock_response(
                saml_identity_provider,
                login_digid_request,
                randstate)
        if saml_identity_provider.authn_binding.endswith("POST"):
            return self._create_saml_authn_submit_response(
                saml_identity_provider,
                login_digid_request,
                randstate)
        if saml_identity_provider.authn_binding.endswith("Redirect"):
            return self._create_saml_authn_redirect_response(saml_identity_provider,
                                                             login_digid_request)
        raise UnexpectedAuthnBinding(
            f"Unknown Authn binding {saml_identity_provider.authn_binding} "
            f"configured in idp metadata: {saml_identity_provider.name}"
        )

    def _create_saml_authn_submit_response(
            self,
            saml_identity_provider,
            login_digid_request,
            randstate,
            status_code: int = 200,
            headers: dict = None,
            media_type: str = None,
            background: BackgroundTask = None
    ):
        try:
            authn_request = saml_identity_provider.create_authn_request(
                login_digid_request.authorize_request.authorization_by_proxy
            )
        except ScopingAttributesNotAllowed as scoping_not_allowed:
            raise AuthorizationByProxyDisabled() from scoping_not_allowed
        template = Template(self._template_txt)
        rendered = template.render({
            "sso_url": authn_request.sso_url,
            "saml_request": authn_request.get_base64_string().decode(),
            "relay_state": randstate,
        }
        )
        return HTMLResponse(
            content=rendered,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background
        )

    def _create_saml_authn_redirect_response(
            self,
            saml_identity_provider,
            login_digid_request,
    ):
        request = {
            "https": "on",
            "http_host": f"https://{saml_identity_provider.name}.{self._saml_base_issuer}",
            "script_name": self._oidc_authorize_endpoint,
            "get_data": login_digid_request.authorize_request.dict(),
        }
        if login_digid_request.authorize_request.authorization_by_proxy:
            log.warning(
                "User attempted to login using authorization by proxy. But is not supported for this IDProvider: %s",
                saml_identity_provider.name,
            )
            raise AuthorizationByProxyDisabled()

        auth = OneLogin_Saml2_Auth(request, custom_base_path=saml_identity_provider.base_dir)
        return RedirectResponse(
            auth.login(
                return_to=login_digid_request.state,
                force_authn=False,
                set_nameid_policy=False,
            )
        )

    def _create_digid_mock_response(self, saml_identity_provider, login_digid_request, randstate,
                                    status_code: int = 200,
                                    headers: dict = None,
                                    media_type: str = None,
                                    background: BackgroundTask = None):
        base64_authn_request = base64.urlsafe_b64encode(
            json.dumps(login_digid_request.authorize_request.dict()).encode()
        ).decode()
        sso_url = f"/digid-mock?state={randstate}&idp_name={saml_identity_provider.name}&authorize_request={base64_authn_request}"

        authn_request = saml_identity_provider.create_authn_request([], [])
        print(self._template_txt)
        template = Template(self._template_txt)
        rendered = template.render({
            "sso_url": sso_url,
            "saml_request": authn_request.get_base64_string().decode(),
            "relay_state": randstate,
        })
        print(rendered)
        return HTMLResponse(
            content=rendered,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background
        )


