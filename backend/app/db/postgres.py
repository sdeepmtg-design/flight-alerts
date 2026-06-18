from datetime import datetime, timezone

import asyncpg

from app.config import settings

MAX_ROUTES = 10

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY,
        origin_iata TEXT,
        push_token TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS routes (
        id SERIAL PRIMARY KEY,
        device_id TEXT NOT NULL REFERENCES devices(device_id),
        destination_iata TEXT NOT NULL,
        max_price INTEGER NOT NULL,
        label TEXT,
        active BOOLEAN DEFAULT TRUE,
        created_at TEXT NOT NULL,
        destination_country TEXT,
        destination_city TEXT,
        trip_class INTEGER DEFAULT 0,
        departure_month TEXT,
        departure_date TEXT,
        date_flex_days INTEGER DEFAULT 0,
        one_way BOOLEAN DEFAULT TRUE,
        UNIQUE (device_id, destination_iata)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_snapshots (
        id SERIAL PRIMARY KEY,
        route_id INTEGER NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
        price INTEGER NOT NULL,
        departure_at TEXT,
        return_at TEXT,
        airline TEXT,
        link TEXT,
        fetched_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts_sent (
        id SERIAL PRIMARY KEY,
        route_id INTEGER NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
        price INTEGER NOT NULL,
        sent_at TEXT NOT NULL
    )
    """,
]

ROUTE_MIGRATIONS = [
    "ALTER TABLE routes ADD COLUMN IF NOT EXISTS destination_country TEXT",
    "ALTER TABLE routes ADD COLUMN IF NOT EXISTS destination_city TEXT",
    "ALTER TABLE routes ADD COLUMN IF NOT EXISTS trip_class INTEGER DEFAULT 0",
    "ALTER TABLE routes ADD COLUMN IF NOT EXISTS departure_month TEXT",
    "ALTER TABLE routes ADD COLUMN IF NOT EXISTS departure_date TEXT",
    "ALTER TABLE routes ADD COLUMN IF NOT EXISTS date_flex_days INTEGER DEFAULT 0",
    "ALTER TABLE routes ADD COLUMN IF NOT EXISTS one_way BOOLEAN DEFAULT TRUE",
]

_pool: asyncpg.Pool | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dsn() -> str:
    url = settings.database_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


def _row(record: asyncpg.Record | None) -> dict | None:
    return dict(record) if record else None


async def init_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(_dsn(), ssl="require", min_size=1, max_size=5)
    assert _pool is not None
    async with _pool.acquire() as conn:
        for sql in SCHEMA_STATEMENTS:
            await conn.execute(sql)
        for sql in ROUTE_MIGRATIONS:
            await conn.execute(sql)
        await _purge_inactive_routes(conn)


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def _purge_inactive_routes(conn: asyncpg.Connection) -> None:
    ids = [
        row["id"]
        for row in await conn.fetch("SELECT id FROM routes WHERE active = FALSE")
    ]
    if not ids:
        return
    await conn.execute(
        "DELETE FROM alerts_sent WHERE route_id = ANY($1::int[])", ids
    )
    await conn.execute(
        "DELETE FROM price_snapshots WHERE route_id = ANY($1::int[])", ids
    )
    await conn.execute("DELETE FROM routes WHERE active = FALSE")


def _pool_required() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


async def ensure_device(device_id: str) -> None:
    now = _now()
    pool = _pool_required()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM devices WHERE device_id = $1", device_id
        )
        if exists:
            return
        await conn.execute(
            "INSERT INTO devices (device_id, origin_iata, push_token, created_at, updated_at) "
            "VALUES ($1, NULL, NULL, $2, $2)",
            device_id,
            now,
        )


async def get_device(device_id: str) -> dict | None:
    pool = _pool_required()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM devices WHERE device_id = $1", device_id
        )
        return _row(row)


async def update_device(
    device_id: str,
    *,
    origin_iata: str | None = None,
    push_token: str | None = None,
) -> dict:
    await ensure_device(device_id)
    now = _now()
    pool = _pool_required()
    async with pool.acquire() as conn:
        if origin_iata is not None:
            await conn.execute(
                "UPDATE devices SET origin_iata = $1, updated_at = $2 WHERE device_id = $3",
                origin_iata.upper(),
                now,
                device_id,
            )
        if push_token is not None:
            await conn.execute(
                "UPDATE devices SET push_token = $1, updated_at = $2 WHERE device_id = $3",
                push_token,
                now,
                device_id,
            )
    device = await get_device(device_id)
    assert device is not None
    return device


async def count_routes(device_id: str) -> int:
    pool = _pool_required()
    async with pool.acquire() as conn:
        value = await conn.fetchval(
            "SELECT COUNT(*) FROM routes WHERE device_id = $1 AND active = TRUE",
            device_id,
        )
        return int(value or 0)


async def list_routes(device_id: str) -> list[dict]:
    pool = _pool_required()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT r.*, ps.price AS last_price, ps.departure_at AS last_departure, "
            "ps.return_at AS last_return, ps.fetched_at AS last_checked "
            "FROM routes r "
            "LEFT JOIN LATERAL ("
            "  SELECT price, departure_at, return_at, fetched_at "
            "  FROM price_snapshots WHERE route_id = r.id "
            "  ORDER BY fetched_at DESC LIMIT 1"
            ") ps ON TRUE "
            "WHERE r.device_id = $1 AND r.active = TRUE "
            "ORDER BY r.id",
            device_id,
        )
        return [dict(r) for r in rows]


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
    if await count_routes(device_id) >= MAX_ROUTES:
        raise ValueError(f"Максимум {MAX_ROUTES} направлений")
    now = _now()
    dest = destination_iata.upper()
    pool = _pool_required()
    async with pool.acquire() as conn:
        active = await conn.fetchrow(
            "SELECT * FROM routes WHERE device_id = $1 AND destination_iata = $2 AND active = TRUE",
            device_id,
            dest,
        )
        if active:
            raise ValueError("Это направление уже добавлено")

        inactive = await conn.fetchrow(
            "SELECT * FROM routes WHERE device_id = $1 AND destination_iata = $2 AND active = FALSE",
            device_id,
            dest,
        )
        if inactive:
            row = await conn.fetchrow(
                "UPDATE routes SET active = TRUE, max_price = $1, label = $2, "
                "destination_country = $3, destination_city = $4, trip_class = $5, departure_month = $6, "
                "departure_date = $7, date_flex_days = $8, one_way = $9 "
                "WHERE id = $10 RETURNING *",
                max_price,
                label,
                destination_country,
                destination_city,
                trip_class,
                departure_month,
                departure_date,
                date_flex_days,
                one_way,
                inactive["id"],
            )
            return dict(row)

        try:
            row = await conn.fetchrow(
                "INSERT INTO routes ("
                "device_id, destination_iata, max_price, label, created_at, "
                "destination_country, destination_city, trip_class, departure_month, departure_date, "
                "date_flex_days, one_way"
                ") VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING *",
                device_id,
                dest,
                max_price,
                label,
                now,
                destination_country,
                destination_city,
                trip_class,
                departure_month,
                departure_date,
                date_flex_days,
                one_way,
            )
        except asyncpg.UniqueViolationError as e:
            raise ValueError("Это направление уже добавлено") from e
        return dict(row)


async def delete_route(device_id: str, route_id: int) -> bool:
    pool = _pool_required()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT id FROM routes WHERE id = $1 AND device_id = $2",
            route_id,
            device_id,
        )
        if not exists:
            return False
        await conn.execute("DELETE FROM alerts_sent WHERE route_id = $1", route_id)
        await conn.execute("DELETE FROM price_snapshots WHERE route_id = $1", route_id)
        result = await conn.execute(
            "DELETE FROM routes WHERE id = $1 AND device_id = $2",
            route_id,
            device_id,
        )
        return result.endswith("DELETE 1")


async def get_active_routes_for_price_check() -> list[dict]:
    pool = _pool_required()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT r.*, d.origin_iata, d.push_token "
            "FROM routes r "
            "JOIN devices d ON d.device_id = r.device_id "
            "WHERE r.active = TRUE AND d.origin_iata IS NOT NULL"
        )
        return [dict(r) for r in rows]


async def save_snapshot(
    route_id: int,
    price: int,
    departure_at: str | None,
    return_at: str | None,
    airline: str | None,
    link: str | None,
) -> None:
    pool = _pool_required()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO price_snapshots "
            "(route_id, price, departure_at, return_at, airline, link, fetched_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            route_id,
            price,
            departure_at,
            return_at,
            airline,
            link,
            _now(),
        )


async def get_last_snapshot(route_id: int) -> dict | None:
    pool = _pool_required()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM price_snapshots WHERE route_id = $1 "
            "ORDER BY fetched_at DESC LIMIT 1",
            route_id,
        )
        return _row(row)


async def get_last_alert(route_id: int) -> dict | None:
    pool = _pool_required()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM alerts_sent WHERE route_id = $1 ORDER BY sent_at DESC LIMIT 1",
            route_id,
        )
        return _row(row)


async def record_alert(route_id: int, price: int) -> None:
    pool = _pool_required()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO alerts_sent (route_id, price, sent_at) VALUES ($1, $2, $3)",
            route_id,
            price,
            _now(),
        )
