import base64

import urllib.parse as urlparse

from lxml import etree

from starlette.datastructures import Headers
from fastapi.responses import RedirectResponse, HTMLResponse

from inge6.models import AuthorizeRequest
from inge6.provider import Provider
from inge6.config import settings

from .test_utils import decode_base64_and_inflate

NAMESPACES = {
    'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
    'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
}

# pylint: disable=redefined-outer-name, unused-argument
def test_authorize_endpoint_digid(digid_config, disable_digid_mock):
    """
    Test if the generated authn request corresponds with the
    expected values when connecting to digid. e.g. a Redirect Binding:

    <samlp:AuthnRequest
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        ID="ONELOGIN_1d940b35a906b780f8574c26fcc4945e8a5d0de9"  Version="2.0"
        IssueInstant="2021-08-13T11:35:43Z"
        AssertionConsumerServiceURL="https://tvs.acc.coronacheck.nl/acs"
        ProviderName="Ministerie van Volksgezondheid, Welzijn en Sport">
        <saml:Issuer>http://sp.example.com</saml:Issuer>
        <samlp:RequestedAuthnContext Comparison="minimum">
            <saml:AuthnContextClassRef>
                urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
            </saml:AuthnContextClassRef>
        </samlp:RequestedAuthnContext>
    </samlp:AuthnRequest>
    """
    provider: Provider = Provider()

    auth_req = AuthorizeRequest(
        client_id="test_client",
        redirect_uri="http://localhost:3000/login",
        response_type="code",
        nonce="n-0S6_WzA2Mj",
        state="af0ifjsldkj",
        scope="openid",
        code_challenge="_1f8tFjAtu6D1Df-GOyDPoMjCJdEvaSWsnqR6SLpzsw", # code_verifier = SoOEDN-mZKNhw7Mc52VXxyiqTvFB3mod36MwPru253c
        code_challenge_method="S256",
    )

    headers = Headers()

    resp: RedirectResponse = provider.authorize_endpoint(auth_req, headers, '0.0.0.0')
    redirect_url = resp.headers.get('location')

    parsed_url = urlparse.urlparse(redirect_url)
    query_params = urlparse.parse_qs(parsed_url.query)
    assert all(key in query_params.keys() for key in ['SAMLRequest', 'RelayState', 'Signature', 'SigAlg'])

    generated_authnreq = decode_base64_and_inflate(query_params['SAMLRequest'][0]).decode()
    # pylint: disable=c-extension-no-member
    parsed_authnreq = etree.fromstring(generated_authnreq).getroottree().getroot()

    assert parsed_authnreq.attrib['ID'] is not None
    assert parsed_authnreq.attrib['IssueInstant'] is not None
    assert parsed_authnreq.attrib['AssertionConsumerServiceURL'] is not None
    assert parsed_authnreq.attrib['ProviderName'] is not None
    assert parsed_authnreq.find('./saml:Issuer', NAMESPACES) is not None

    assert parsed_authnreq.find('./saml:Issuer', NAMESPACES).text == settings.issuer
    assert parsed_authnreq.find('./samlp:RequestedAuthnContext', NAMESPACES).attrib['Comparison'] == 'minimum' is not None
    assert parsed_authnreq.find('.//saml:AuthnContextClassRef', NAMESPACES) is not None
    assert parsed_authnreq.find('.//saml:AuthnContextClassRef', NAMESPACES).text == 'urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract'


# pylint: disable=redefined-outer-name, unused-argument
def test_authorize_endpoint_tvs(tvs_config):
    """
    Test if the generated authn request corresponds with the
    structure when connecting to tvs. e.g. a POST Binding:

    <samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
            Version="2.0" ForceAuthn="true"
            AssertionConsumerServiceIndex="1" AttributeConsumingServiceIndex="1"
            ID="_32d4a5dd3c99cd03e25c5eaaf1c15e251103a514cac58cc3a556ed2a1812d712389355e84f19670cca"
            Destination="/digid-mock?state=07a3865faac4f1e8b08f88cb6a7a656b684a1f0f39e3e9f1b0e30a7464dbb4da"
            IssueInstant="2021-08-17T13:28:16Z">
    <saml:Issuer>https://localhost:8007</saml:Issuer>
    <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:SignedInfo>
            <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
            <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
            <ds:Reference URI="#_32d4a5dd3c99cd03e25c5eaaf1c15e251103a514cac58cc3a556ed2a1812d712389355e84f19670cca">
                <ds:Transforms>
                    <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                    <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                </ds:Transforms>
                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                <ds:DigestValue>6m+p3/2Fe1s2YYogNwrx7pYn9DAYb1FrBIFzGy5yPmQ=</ds:DigestValue>
            </ds:Reference>
        </ds:SignedInfo>
        <ds:SignatureValue>...</ds:SignatureValue>
            <ds:KeyInfo>
                <ds:KeyName/>
                <ds:X509Data>
                    <ds:X509Certificate>...</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </ds:Signature>
    </samlp:AuthnRequest>
    """

    def get_post_params_from_html(html: str):
        # pylint: disable=c-extension-no-member
        html_autosubmit = etree.fromstring(html)
        post_form = html_autosubmit.find('.//form')
        saml_req = post_form.find("./input[@name='SAMLRequest']").attrib['value']
        relay_state = post_form.find("./input[@name='RelayState']").attrib['value']

        return {
            'SAMLRequest': saml_req,
            'relay_state': relay_state
        }

    provider: Provider = Provider()
    auth_req = AuthorizeRequest(
        client_id="test_client",
        redirect_uri="http://localhost:3000/login",
        response_type="code",
        nonce="n-0S6_WzA2Mj",
        state="af0ifjsldkj",
        scope="openid",
        code_challenge="_1f8tFjAtu6D1Df-GOyDPoMjCJdEvaSWsnqR6SLpzsw", # code_verifier = SoOEDN-mZKNhw7Mc52VXxyiqTvFB3mod36MwPru253c
        code_challenge_method="S256",
    )

    headers = Headers()

    resp: HTMLResponse = provider.authorize_endpoint(auth_req, headers, '0.0.0.0')
    saml_request = get_post_params_from_html(resp.body)['SAMLRequest']
    generated_authnreq = base64.b64decode(saml_request).decode()
    # pylint: disable=c-extension-no-member
    parsed_authnreq = etree.fromstring(generated_authnreq).getroottree().getroot()

    assert parsed_authnreq.attrib['ID'] is not None
    assert parsed_authnreq.attrib['IssueInstant'] is not None
    assert parsed_authnreq.attrib['AssertionConsumerServiceIndex'] is not None
    assert parsed_authnreq.find('./saml:Issuer', NAMESPACES) is not None

    assert parsed_authnreq.find('./saml:Issuer', NAMESPACES).text == settings.issuer
    assert parsed_authnreq.find('./ds:Signature', NAMESPACES) is not None
    assert parsed_authnreq.find('.//ds:SignatureValue', NAMESPACES) is not None
