"""Application errors that avoid exposing credentials or provider URLs."""

from __future__ import annotations


class ProviderRequestError(RuntimeError):
    def __init__(self, provider: str, status_code: int | None, message: str) -> None:
        self.provider = provider
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class ConnectorNotConfiguredError(RuntimeError):
    def __init__(self, connector: str) -> None:
        self.connector = connector
        super().__init__(f"Credential untuk connector {connector} belum dikonfigurasi")
