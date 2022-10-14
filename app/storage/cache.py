from typing import Any, Text, Optional
import abc


class Cache(abc.ABC):
    @abc.abstractmethod
    def incr(self, key: str) -> int:
        pass

    @abc.abstractmethod
    def expire(self, key: str, time_in_seconds: int) -> None:
        pass

    @abc.abstractmethod
    def set(self, key: str, value: Any) -> None:
        pass

    @abc.abstractmethod
    def set_complex_object(self, key: str, value: Any) -> None:
        pass

    @abc.abstractmethod
    def get_complex_object(self, key: str) -> Any:
        pass

    @abc.abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abc.abstractmethod
    def get_int(self, key: str) -> Optional[int]:
        pass

    @abc.abstractmethod
    def get_string(self, key: str) -> Optional[str]:
        pass

    @abc.abstractmethod
    def get_bool(self, key: str) -> bool:
        pass

    @abc.abstractmethod
    def gen_token(self) -> Text:
        pass
