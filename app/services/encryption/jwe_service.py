import abc

# todo: Define interface with pubkey from client ed25519 and rsa typed
from typing import Dict, Any

from jwcrypto.jwt import JWK


class JweService(abc.ABC):
    @abc.abstractmethod
    def get_pub_jwk(self) -> JWK:
        pass

    @abc.abstractmethod
    def to_jwe(self, data: Dict[str, Any], pubkey: str) -> str:
        pass
