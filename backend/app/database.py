from app.config import settings

if settings.database_url:
    from app.db import postgres as _backend
else:
    from app.db import sqlite as _backend

MAX_ROUTES = _backend.MAX_ROUTES


async def init_db() -> None:
    await _backend.init_db()


async def close_db() -> None:
    await _backend.close_db()


async def ensure_device(device_id: str) -> None:
    await _backend.ensure_device(device_id)


async def get_device(device_id: str) -> dict | None:
    return await _backend.get_device(device_id)


async def update_device(
    device_id: str,
    *,
    origin_iata: str | None = None,
    push_token: str | None = None,
) -> dict:
    return await _backend.update_device(
        device_id, origin_iata=origin_iata, push_token=push_token
    )


async def count_routes(device_id: str) -> int:
    return await _backend.count_routes(device_id)


async def list_routes(device_id: str) -> list[dict]:
    return await _backend.list_routes(device_id)


async def add_route(
    device_id: str,
    destination_iata: str,
    max_price: int,
    label: str | None = None,
    *,
    destination_country: str | None = None,
    destination_city: str | None = None,
    trip_class: int = 0,
    departure_month: str | None = None,
    departure_date: str | None = None,
    date_flex_days: int = 0,
    one_way: bool = True,
) -> dict:
    return await _backend.add_route(
        device_id,
        destination_iata,
        max_price,
        label,
        destination_country=destination_country,
        destination_city=destination_city,
        trip_class=trip_class,
        departure_month=departure_month,
        departure_date=departure_date,
        date_flex_days=date_flex_days,
        one_way=one_way,
    )


async def delete_route(device_id: str, route_id: int) -> bool:
    return await _backend.delete_route(device_id, route_id)


async def get_active_routes_for_price_check() -> list[dict]:
    return await _backend.get_active_routes_for_price_check()


async def save_snapshot(
    route_id: int,
    price: int,
    departure_at: str | None,
    return_at: str | None,
    airline: str | None,
    link: str | None,
) -> None:
    await _backend.save_snapshot(
        route_id, price, departure_at, return_at, airline, link
    )


async def get_last_snapshot(route_id: int) -> dict | None:
    return await _backend.get_last_snapshot(route_id)


async def get_last_alert(route_id: int) -> dict | None:
    return await _backend.get_last_alert(route_id)


async def record_alert(route_id: int, price: int) -> None:
    await _backend.record_alert(route_id, price)
