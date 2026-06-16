from fastapi import APIRouter, Depends, HTTPException

from app import database as db
from app.api.deps import get_device_id
from app.schemas import CheckResult, DeviceOut, DeviceUpdate, RouteCreate, RouteOut
from app.services import monitor

router = APIRouter()


def _route_out(row: dict) -> RouteOut:
    return RouteOut(
        id=row["id"],
        destination_iata=row["destination_iata"],
        destination_country=row.get("destination_country"),
        destination_city=row.get("destination_city"),
        max_price=row["max_price"],
        label=row.get("label"),
        trip_class=int(row.get("trip_class") or 0),
        departure_month=row.get("departure_month"),
        departure_date=row.get("departure_date"),
        date_flex_days=int(row.get("date_flex_days") or 0),
        one_way=bool(row.get("one_way", 1)),
        last_price=row.get("last_price"),
        last_departure=row.get("last_departure"),
        last_return=row.get("last_return"),
        last_checked=row.get("last_checked"),
    )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/me", response_model=DeviceOut)
async def me(device_id: str = Depends(get_device_id)) -> DeviceOut:
    device = await db.get_device(device_id)
    count = await db.count_routes(device_id)
    return DeviceOut(
        device_id=device_id,
        origin_iata=device["origin_iata"] if device else None,
        routes_count=count,
    )


@router.patch("/me", response_model=DeviceOut)
async def update_me(
    body: DeviceUpdate,
    device_id: str = Depends(get_device_id),
) -> DeviceOut:
    device = await db.update_device(
        device_id,
        origin_iata=body.origin_iata,
        push_token=body.push_token,
    )
    count = await db.count_routes(device_id)
    return DeviceOut(
        device_id=device_id,
        origin_iata=device["origin_iata"],
        routes_count=count,
    )


@router.get("/routes", response_model=list[RouteOut])
async def list_routes(device_id: str = Depends(get_device_id)) -> list[RouteOut]:
    rows = await db.list_routes(device_id)
    return [_route_out(r) for r in rows]


@router.post("/routes", response_model=RouteOut, status_code=201)
async def create_route(
    body: RouteCreate,
    device_id: str = Depends(get_device_id),
) -> RouteOut:
    device = await db.get_device(device_id)
    if not device or not device.get("origin_iata"):
        raise HTTPException(400, "Сначала укажите город вылета в настройках")
    try:
        label = body.label or (
            f"{body.destination_city}, {body.destination_country}"
            if body.destination_city and body.destination_country
            else body.destination_city
        )
        row = await db.add_route(
            device_id,
            body.destination_iata,
            body.max_price,
            label,
            destination_country=body.destination_country,
            destination_city=body.destination_city,
            trip_class=body.trip_class,
            departure_month=body.departure_month,
            departure_date=body.departure_date,
            date_flex_days=body.date_flex_days,
            one_way=body.one_way,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _route_out(row)


@router.delete("/routes/{route_id}", status_code=204)
async def remove_route(route_id: int, device_id: str = Depends(get_device_id)) -> None:
    if not await db.delete_route(device_id, route_id):
        raise HTTPException(404, "Маршрут не найден")


@router.post("/internal/check-prices", response_model=CheckResult)
async def check_prices(secret: str) -> CheckResult:
    from app.config import settings

    if secret != settings.cron_secret:
        raise HTTPException(403, "Forbidden")
    checked, alerts = await monitor.run_price_check()
    return CheckResult(checked=checked, alerts_sent=alerts)
