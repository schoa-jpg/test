import time

import aiohttp

API_URL = "https://open.er-api.com/v6/latest/USD"
CACHE_TTL = 60 * 60

POPULAR = ["USD", "EUR", "RUB", "GBP", "JPY", "CNY", "KZT", "UAH"]

_rates_cache = None
_rates_fetched_at = 0.0


def fmt(n: float, digits: int = 2) -> str:
    return f"{n:,.{digits}f}".replace(",", " ")


async def get_rates() -> dict:
    global _rates_cache, _rates_fetched_at
    now = time.time()
    if _rates_cache and now - _rates_fetched_at < CACHE_TTL:
        return _rates_cache

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as resp:
            if resp.status != 200:
                raise RuntimeError(f"API вернул ошибку (HTTP {resp.status})")
            data = await resp.json()
            if data.get("result") != "success":
                raise RuntimeError(data.get("error-type", "Неизвестная ошибка"))
            _rates_cache = data["rates"]
            _rates_fetched_at = now
            return _rates_cache


async def convert(amount: float, cur_from: str, cur_to: str) -> tuple[float, float]:
    rates = await get_rates()
    cur_from = cur_from.upper()
    cur_to = cur_to.upper()
    if cur_from not in rates:
        raise ValueError(f"Неизвестная валюта: {cur_from}")
    if cur_to not in rates:
        raise ValueError(f"Неизвестная валюта: {cur_to}")
    per_unit = rates[cur_to] / rates[cur_from]
    return amount * per_unit, per_unit


async def popular_rates(base: str = "RUB") -> list[tuple[str, float]]:
    rates = await get_rates()
    base = base.upper()
    if base not in rates:
        raise ValueError(f"Неизвестная валюта: {base}")
    return [(code, rates[base] / rates[code]) for code in POPULAR if code != base and code in rates]
