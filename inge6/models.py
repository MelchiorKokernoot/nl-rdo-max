# pylint: disable=too-few-public-methods
import html
import json
import base64
import typing

from enum import Enum

from jinja2 import Template

from starlette.background import BackgroundTask
from starlette.datastructures import URL
from starlette.responses import HTMLResponse

from pydantic import BaseModel, validator

from fastapi import Form
from fastapi.responses import RedirectResponse

from inge6.config import Settings
from inge6.saml.saml_request import AuthNRequest


def _fill_template(template_txt: str, context: dict):
    template = Template(template_txt)
    rendered = template.render(context)

    return rendered


def _fill_template_from_file(filename: str, context: dict) -> typing.Text:
    with open(filename, 'r', encoding='utf-8') as template_file:
        template_txt = template_file.read()

    return _fill_template(template_txt, context)


class AuthorizeErrorRedirectResponse(RedirectResponse):

    def __init__(self,
                 url: typing.Union[str, URL],
                 error: str,
                 error_description: str,
                 state: str, status_code: int = 307,
                 headers: dict = None,
                 background: BackgroundTask = None
    ) -> None:
        super().__init__(url, status_code=status_code, headers=headers, background=background)
        self.error = error
        self.error_description = error_description
        self.state = state
        self.headers['location'] += f"?error={error}&error_description={error_description}&state={state}"


class RateLimitRedirectResponse(RedirectResponse):

    def __init__(self,
                 url: typing.Union[str, URL],
                 next_redirect_uri: str,
                 client_id: str,
                 state: str, status_code: int = 307,
                 headers: dict = None,
                 background: BackgroundTask = None
    ) -> None:
        super().__init__(url, status_code=status_code, headers=headers, background=background)
        self.next_redirect_uri = next_redirect_uri
        self.client_id = client_id
        self.state = state
        self.headers['location'] += f"?redirect_uri={next_redirect_uri}&client_id={client_id}&state={state}"


class SAMLAuthNRedirectResponse(RedirectResponse):
    pass


class SAMLAuthNAutoSubmitResponse(HTMLResponse):

    def __init__(self,
                 sso_url: str,
                 relay_state: str,
                 authn_request: AuthNRequest,
                 settings: Settings,
                 status_code: int = 200,
                 headers: dict = None,
                 media_type: str = None,
                 background: BackgroundTask = None
    ) -> None:
        self.sso_url = sso_url
        self.relay_state = relay_state
        self.authn_request = authn_request
        self.settings = settings
        content = self.create_post_autosubmit_form({
            'sso_url': self.sso_url,
            'saml_request': self.authn_request.get_base64_string().decode(),
            'relay_state': self.relay_state
        })
        super().__init__(content=content, status_code=status_code, headers=headers, media_type=media_type, background=background)

    def create_post_autosubmit_form(self, context: dict) -> typing.Text:
        return _fill_template_from_file(self.settings.saml.authn_request_html_template, context)


class MetaRedirectResponse(HTMLResponse):

    def __init__(self, redirect_url: str, status_code: int = 200, headers: dict = None, media_type: str = None, background: BackgroundTask = None) -> None:
        self.redirect_url = redirect_url
        self.template = "saml/templates/html/assertion_consumer_service.html"
        content=self.create_acs_redirect_link({"redirect_url": self.redirect_url})
        super().__init__(content=content, status_code=status_code, headers=headers, media_type=media_type, background=background)

    def create_acs_redirect_link(self, context: dict) -> typing.Text:
        return _fill_template_from_file(self.template, context)


class SomethingWrongHTMLResponse(HTMLResponse):

    def __init__(self,
                 redirect_uri: str,
                 template_head: str,
                 template_tail: str,
                 status_code: int = 200,
                 headers: dict = None,
                 media_type: str = None,
                 background: BackgroundTask = None
    ) -> None:
        self.redirect_uri = redirect_uri
        content = template_head + self.redirect_uri + template_tail
        super().__init__(content=content, status_code=status_code, headers=headers, media_type=media_type, background=background)


class JWTToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    id_token: str


class JWTError(BaseModel):
    error: str
    error_description: str

JWTResponse = typing.Union[JWTToken, JWTError]

class ResponseType(str, Enum):
    CODE: str = "code"

    def __str__(self) -> str: # pylint: disable=invalid-str-returned
        return self.CODE

class AuthorizeRequest(BaseModel):
    client_id: str
    redirect_uri: str
    response_type: ResponseType
    nonce: str
    scope: str
    state: str
    code_challenge: str
    code_challenge_method: str

class LoginDigiDRequest(BaseModel):
    state: str
    authorize_request: AuthorizeRequest
    force_digid: typing.Optional[bool] = None
    idp_name: typing.Optional[str] = None

    @validator('state')
    def convert_to_escaped_html(cls, text): # pylint: disable=no-self-argument, no-self-use
        return html.escape(text)

    @classmethod
    def from_request(
        cls,
        state: str,
        authorize_request: str,
        force_digid: typing.Optional[bool] = None,
        idp_name: typing.Optional[str] = None
    ) -> 'LoginDigiDRequest':
        return LoginDigiDRequest.parse_obj({
            'state': state,
            'authorize_request': AuthorizeRequest(
                **json.loads(
                    base64.urlsafe_b64decode(
                        authorize_request
                    )
                )
            ),
            'force_digid': force_digid,
            'idp_name': idp_name
        })

class DigiDMockRequest(BaseModel):
    state: str
    SAMLRequest: str
    RelayState: str
    idp_name: str
    authorize_request: str

    # pylint: disable=invalid-name
    @classmethod
    def from_request(
        cls,
        state: str,
        idp_name: str,
        authorize_request: str, # base64 encoded
        SAMLRequest: str = Form(...),
        RelayState: str = Form(...),
    ) -> 'DigiDMockRequest':
        return DigiDMockRequest.parse_obj({
            'SAMLRequest': SAMLRequest,
            'RelayState': RelayState,
            'idp_name': idp_name,
            'state': state,
            'authorize_request': authorize_request,
        })

    @validator('state', 'RelayState', 'SAMLRequest')
    def convert_to_escaped_html(cls, text): # pylint: disable=no-self-argument, no-self-use
        return html.escape(text)

class DigiDMockCatchRequest(BaseModel):
    bsn: str
    SAMLart: str
    RelayState: str

    @validator('bsn', 'SAMLart', 'RelayState')
    def convert_to_escaped_html(cls, text): # pylint: disable=no-self-argument, no-self-use
        return html.escape(text)

class SorryPageRequest(BaseModel):
    state: str
    redirect_uri: str
    client_id: str

    @validator('state', 'redirect_uri', 'client_id')
    def convert_to_escaped_html(cls, text): # pylint: disable=no-self-argument, no-self-use
        return html.escape(text)

class AccesstokenRequest(BaseModel):
    code: str
    code_verifier: str
    state: str
    grant_type: str
    redirect_uri: str

    @classmethod
    def as_form(
        cls,
        code: str = Form(...),
        code_verifier: str = Form(...),
        state: str = Form(...),
        grant_type: str = Form(...),
        redirect_uri: str = Form(...)
    ):
        return cls(
                code=code,
                code_verifier=code_verifier,
                state=state,
                grant_type=grant_type,
                redirect_uri=redirect_uri
        )
