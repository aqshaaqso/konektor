"""Credential-safe gateway for EnsembleData."""

from __future__ import annotations

from social_connectors_api.errors import ProviderRequestError
from social_connectors_api.http_client import JsonHttpClient, JsonHttpClientProtocol
from social_connectors_api.models import JsonObject


class EnsembleDataClient:
    base_url = "https://ensembledata.com/apis"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 30,
        http_client: JsonHttpClientProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._http_client = http_client or JsonHttpClient(timeout_seconds)

    def get_json(self, endpoint: str, params: dict[str, str]) -> JsonObject:
        safe_params = {**params, "token": self._api_key}
        try:
            return self._http_client.get_json(
                f"{self.base_url}{endpoint}", safe_params, "EnsembleData"
            )
        except ProviderRequestError as exc:
            messages = {
                400: "Parameter request tidak diterima oleh EnsembleData",
                401: "Token EnsembleData tidak valid",
                403: "Token EnsembleData tidak memiliki izin untuk endpoint ini",
                404: "Endpoint atau data tidak ditemukan di EnsembleData",
                429: "Batas request EnsembleData sedang tercapai",
                491: "Token EnsembleData tidak valid",
                492: "Email akun EnsembleData belum diverifikasi",
                493: "Langganan EnsembleData sudah berakhir",
                495: "Unit harian EnsembleData sudah habis",
            }
            message = messages.get(exc.status_code, exc.message)
            raise ProviderRequestError("EnsembleData", exc.status_code, message) from None
