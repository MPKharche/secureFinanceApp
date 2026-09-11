from datetime import date
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.providers.base import FxRateProvider

BASE_URL = "https://api.frankfurter.app"


class FrankfurterProvider(FxRateProvider):
    """FX rates from Frankfurter (ECB). No API key. Omits currencies ECB does not publish."""

    @property
    def name(self) -> str:
        return "frankfurter"

    def _supported(self) -> set[str]:
        return {code.strip() for code in get_settings().supported_currencies.split(",") if code.strip()}

    def _parse_rates(self, data: dict) -> dict[str, Decimal]:
        supported = self._supported()
        return {
            code: Decimal(str(rate))
            for code, rate in data.get("rates", {}).items()
            if code in supported
        }

    async def fetch_latest(self) -> dict[str, Decimal]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/latest", params={"from": "USD"})
            resp.raise_for_status()
            data = resp.json()
        return self._parse_rates(data)

    async def fetch_historical(self, target_date: date) -> dict[str, Decimal]:
        date_str = target_date.strftime("%Y-%m-%d")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/{date_str}", params={"from": "USD"})
            resp.raise_for_status()
            data = resp.json()
        return self._parse_rates(data)
