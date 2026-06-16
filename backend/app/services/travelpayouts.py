"""Клиент Aviasales Data API (Travelpayouts)."""

from datetime import date, timedelta

import httpx

from app.config import settings

API_BASE = "https://api.travelpayouts.com/aviasales/v3"


def _month_range(months_ahead: int = 4) -> list[str]:
    today = date.today()
    y, m = today.year, today.month
    out: list[str] = []
    for _ in range(months_ahead):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _next_month(ym: str) -> str:
    y, m = map(int, ym.split("-"))
    m += 1
    if m > 12:
        m = 1
        y += 1
    return f"{y:04d}-{m:02d}"


def build_search_dates(
    departure_month: str | None,
    departure_date: str | None,
    date_flex_days: int,
) -> list[str]:
    """
    Ключи для departure_at в API: YYYY-MM или YYYY-MM-DD.
    date_flex_days=3 → ±3 дня вокруг departure_date.
    departure_month → только этот месяц.
    иначе → 4 ближайших месяца.
    """
    if departure_date and date_flex_days >= 3:
        d = date.fromisoformat(departure_date)
        return [(d + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(-3, 4)]
    if departure_date:
        return [departure_date]
    if departure_month:
        return [departure_month]
    return _month_range(4)


def build_return_at(
    one_way: bool,
    departure_month: str | None,
    departure_date: str | None,
) -> str | None:
    if one_way:
        return None
    if departure_date:
        d = date.fromisoformat(departure_date)
        return (d + timedelta(days=7)).strftime("%Y-%m-%d")
    if departure_month:
        return _next_month(departure_month)
    months = _month_range(4)
    return months[1] if len(months) > 1 else None


def build_booking_url(link: str | None) -> str | None:
    if not link:
        return None
    path = link if link.startswith("/") else f"/{link}"
    base = settings.aviasales_base.rstrip("/")
    url = f"{base}{path}"
    marker = settings.travelpayouts_marker
    if marker:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}marker={marker}"
    return url


async def cheapest_for_route(
    origin: str,
    destination: str,
    *,
    one_way: bool = True,
    trip_class: int = 0,
    departure_month: str | None = None,
    departure_date: str | None = None,
    date_flex_days: int = 0,
) -> dict | None:
    if not settings.travelpayouts_token:
        return None

    search_dates = build_search_dates(departure_month, departure_date, date_flex_days)
    return_at = build_return_at(one_way, departure_month, departure_date)
    best: dict | None = None
    headers = {"Accept-Encoding": "gzip, deflate"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for dep_key in search_dates:
            params = {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_at": dep_key,
                "one_way": "true" if one_way else "false",
                "sorting": "price",
                "direct": "false",
                "trip_class": int(trip_class),
                "cy": "rub",
                "limit": 10,
                "page": 1,
                "token": settings.travelpayouts_token,
            }
            if return_at and not one_way:
                params["return_at"] = return_at
            r = await client.get(
                f"{API_BASE}/prices_for_dates",
                params=params,
                headers=headers,
            )
            r.raise_for_status()
            body = r.json()
            if not body.get("success"):
                continue
            for item in body.get("data") or []:
                price = item.get("price")
                if price is None:
                    continue
                if best is None or price < best["price"]:
                    best = {
                        "price": int(price),
                        "departure_at": item.get("departure_at"),
                        "return_at": item.get("return_at"),
                        "airline": item.get("airline"),
                        "link": build_booking_url(item.get("link")),
                    }
    return best
