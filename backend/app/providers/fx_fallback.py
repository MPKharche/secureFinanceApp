import logging
from datetime import date
from decimal import Decimal

import httpx

from app.providers.base import FxRateProvider

logger = logging.getLogger(__name__)


class FallbackFxRateProvider(FxRateProvider):
    """Try primary; on missing config or HTTP failure, use fallback."""

    def __init__(self, primary: FxRateProvider, fallback: FxRateProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self._last = primary

    @property
    def name(self) -> str:
        return self._last.name

    async def fetch_latest(self) -> dict[str, Decimal]:
        return await self._call("fetch_latest")

    async def fetch_historical(self, target_date: date) -> dict[str, Decimal]:
        return await self._call("fetch_historical", target_date)

    async def _call(self, method: str, *args) -> dict[str, Decimal]:
        try:
            rates = await getattr(self._primary, method)(*args)
            self._last = self._primary
            return rates
        except (ValueError, httpx.HTTPError) as exc:
            logger.warning(
                "FX primary %s failed (%s); using %s",
                self._primary.name,
                exc,
                self._fallback.name,
            )
            rates = await getattr(self._fallback, method)(*args)
            self._last = self._fallback
            return rates
