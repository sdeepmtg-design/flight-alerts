from datetime import datetime, timezone

from app import database as db
from app.services import push, travelpayouts

ALERT_DROP_PERCENT = 10


def _parse_dt(value: str | None) -> str:
    if not value:
        return "даты уточняйте на Aviasales"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return value[:10]


def _should_alert(route: dict, price: int, last_snapshot: dict | None, last_alert: dict | None) -> bool:
    if price > route["max_price"]:
        return False
    if last_alert is None:
        return True
    if last_alert["price"] <= price:
        return False
    drop = (last_alert["price"] - price) / last_alert["price"] * 100
    return drop >= ALERT_DROP_PERCENT


async def run_price_check() -> tuple[int, int]:
    routes = await db.get_active_routes_for_price_check()
    alerts_sent = 0

    for route in routes:
        deal = await travelpayouts.cheapest_for_route(
            route["origin_iata"],
            route["destination_iata"],
            one_way=bool(route.get("one_way", 1)),
            departure_month=route.get("departure_month"),
            departure_date=route.get("departure_date"),
            date_flex_days=int(route.get("date_flex_days") or 0),
        )
        if not deal:
            continue

        price = deal["price"]
        last = await db.get_last_snapshot(route["id"])
        await db.save_snapshot(
            route["id"],
            price,
            deal.get("departure_at"),
            deal.get("return_at"),
            deal.get("airline"),
            deal.get("link"),
        )

        push_token = route.get("push_token")
        if not push_token:
            continue

        last_alert = await db.get_last_alert(route["id"])
        if not _should_alert(route, price, last, last_alert):
            continue

        origin = route["origin_iata"]
        dest = route["destination_iata"]
        label = route.get("label") or dest
        dep = _parse_dt(deal.get("departure_at"))
        title = f"✈️ {origin} → {dest}: {price:,} ₽".replace(",", " ")
        body = f"{label}: вылет {dep}, порог {route['max_price']:,} ₽".replace(",", " ")

        ok = await push.send_expo_push(
            route["push_token"],
            title,
            body,
            data={
                "route_id": route["id"],
                "price": price,
                "url": deal.get("link"),
            },
        )
        if ok:
            await db.record_alert(route["id"], price)
            alerts_sent += 1

    return len(routes), alerts_sent
