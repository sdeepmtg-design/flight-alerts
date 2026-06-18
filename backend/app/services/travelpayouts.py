"""Клиент Aviasales Data API (Travelpayouts)."""

from datetime import date, timedelta

import httpx

from app.config import settings

API_V3 = "https://api.travelpayouts.com/aviasales/v3"
API_V2 = "https://api.travelpayouts.com/v2/prices"


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


def _months_for_matrix(search_dates: list[str]) -> list[str]:
    months: set[str] = set()
    for key in search_dates:
        ym = key[:7]
        months.add(f"{ym}-01")
    return sorted(months)


def _matches_departure(
    depart_date: str,
    search_dates: list[str],
    date_flex_days: int,
) -> bool:
    if not depart_date:
        return False
    dep = date.fromisoformat(depart_date[:10])
    for key in search_dates:
        if len(key) == 7:
            if depart_date.startswith(key):
                return True
            continue
        target = date.fromisoformat(key)
        if date_flex_days >= 3:
            if abs((dep - target).days) <= 3:
                return True
        elif dep == target:
            return True
    return False


def _pick_best(current: dict | None, candidate: dict) -> dict:
    if current is None or candidate["price"] < current["price"]:
        return candidate
    return current


async def _cheapest_economy(
    client: httpx.AsyncClient,
    *,
    origin: str,
    destination: str,
    one_way: bool,
    search_dates: list[str],
    return_at: str | None,
    headers: dict[str, str],
) -> dict | None:
    """Эконом: prices_for_dates (v3). trip_class там не поддерживается."""
    best: dict | None = None
    for dep_key in search_dates:
        params = {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departure_at": dep_key,
            "one_way": "true" if one_way else "false",
            "sorting": "price",
            "direct": "false",
            "cy": "rub",
            "limit": 10,
            "page": 1,
            "token": settings.travelpayouts_token,
        }
        if return_at and not one_way:
            params["return_at"] = return_at
        r = await client.get(f"{API_V3}/prices_for_dates", params=params, headers=headers)
        r.raise_for_status()
        body = r.json()
        if not body.get("success"):
            continue
        for item in body.get("data") or []:
            price = item.get("price")
            if price is None:
                continue
            best = _pick_best(
                best,
                {
                    "price": int(price),
                    "departure_at": item.get("departure_at"),
                    "return_at": item.get("return_at"),
                    "airline": item.get("airline"),
                    "link": build_booking_url(item.get("link")),
                },
            )
    return best


async def _cheapest_by_class(
    client: httpx.AsyncClient,
    *,
    origin: str,
    destination: str,
    one_way: bool,
    trip_class: int,
    search_dates: list[str],
    date_flex_days: int,
    headers: dict[str, str],
) -> dict | None:
    """
    Бизнес / первый: month-matrix (v2) с trip_class.
    prices_for_dates игнорирует класс и всегда отдаёт эконом.
    """
    best: dict | None = None
    has_day_filter = any(len(key) == 10 for key in search_dates)

    for month in _months_for_matrix(search_dates):
        params = {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "month": month,
            "currency": "rub",
            "show_to_affiliates": "true",
            "trip_class": int(trip_class),
            "one_way": "true" if one_way else "false",
            "limit": 31,
            "token": settings.travelpayouts_token,
        }
        if not one_way:
            params["trip_duration"] = 1

        r = await client.get(f"{API_V2}/month-matrix", params=params, headers=headers)
        r.raise_for_status()
        body = r.json()
        if not body.get("success"):
            continue

        for item in body.get("data") or []:
            if int(item.get("trip_class", -1)) != trip_class:
                continue
            depart = item.get("depart_date") or ""
            if has_day_filter and not _matches_departure(
                depart, search_dates, date_flex_days
            ):
                continue
            price = item.get("value")
            if price is None:
                continue
            dep_at = depart if "T" in depart else f"{depart}T12:00:00+00:00"
            ret = item.get("return_date") or None
            ret_at = (
                f"{ret}T12:00:00+00:00"
                if ret and "T" not in ret
                else ret
            )
            best = _pick_best(
                best,
                {
                    "price": int(price),
                    "departure_at": dep_at,
                    "return_at": ret_at,
                    "airline": None,
                    "link": None,
                },
            )
    return best


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
    headers = {"Accept-Encoding": "gzip, deflate"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        if trip_class == 0:
            return await _cheapest_economy(
                client,
                origin=origin,
                destination=destination,
                one_way=one_way,
                search_dates=search_dates,
                return_at=return_at,
                headers=headers,
            )
        return await _cheapest_by_class(
            client,
            origin=origin,
            destination=destination,
            one_way=one_way,
            trip_class=trip_class,
            search_dates=search_dates,
            date_flex_days=date_flex_days,
            headers=headers,
        )
