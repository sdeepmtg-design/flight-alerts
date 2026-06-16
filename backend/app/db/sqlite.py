from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.config import settings

MAX_ROUTES = 10

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    origin_iata TEXT,
    push_token TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    destination_iata TEXT NOT NULL,
    max_price INTEGER NOT NULL,
    label TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    UNIQUE (device_id, destination_iata)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    price INTEGER NOT NULL,
    departure_at TEXT,
    return_at TEXT,
    airline TEXT,
    link TEXT,
    fetched_at TEXT NOT NULL,
    FOREIGN KEY (route_id) REFERENCES routes(id)
);

CREATE TABLE IF NOT EXISTS alerts_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    price INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    FOREIGN KEY (route_id) REFERENCES routes(id)
);
"""

ROUTE_MIGRATIONS = [
    "ALTER TABLE routes ADD COLUMN destination_country TEXT",
    "ALTER TABLE routes ADD COLUMN destination_city TEXT",
    "ALTER TABLE routes ADD COLUMN trip_class INTEGER DEFAULT 0",
    "ALTER TABLE routes ADD COLUMN departure_month TEXT",
    "ALTER TABLE routes ADD COLUMN departure_date TEXT",
    "ALTER TABLE routes ADD COLUMN date_flex_days INTEGER DEFAULT 0",
    "ALTER TABLE routes ADD COLUMN one_way INTEGER DEFAULT 1",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.executescript(SCHEMA)
        for sql in ROUTE_MIGRATIONS:
            try:
                await db.execute(sql)
            except aiosqlite.OperationalError:
                pass
        await _purge_inactive_routes(db)
        await db.commit()


async def close_db() -> None:
    pass


async def _purge_inactive_routes(db: aiosqlite.Connection) -> None:
    cur = await db.execute("SELECT id FROM routes WHERE active = 0")
    ids = [row[0] for row in await cur.fetchall()]
    for route_id in ids:
        await db.execute("DELETE FROM alerts_sent WHERE route_id = ?", (route_id,))
        await db.execute("DELETE FROM price_snapshots WHERE route_id = ?", (route_id,))
    if ids:
        await db.execute("DELETE FROM routes WHERE active = 0")


async def ensure_device(device_id: str) -> None:
    now = _now()
    async with aiosqlite.connect(settings.database_path) as db:
        cur = await db.execute(
            "SELECT device_id FROM devices WHERE device_id = ?", (device_id,)
        )
        if await cur.fetchone():
            return
        await db.execute(
            "INSERT INTO devices (device_id, origin_iata, push_token, created_at, updated_at) "
            "VALUES (?, NULL, NULL, ?, ?)",
            (device_id, now, now),
        )
        await db.commit()


async def get_device(device_id: str) -> dict | None:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def update_device(
    device_id: str,
    *,
    origin_iata: str | None = None,
    push_token: str | None = None,
) -> dict:
    await ensure_device(device_id)
    now = _now()
    async with aiosqlite.connect(settings.database_path) as db:
        if origin_iata is not None:
            await db.execute(
                "UPDATE devices SET origin_iata = ?, updated_at = ? WHERE device_id = ?",
                (origin_iata.upper(), now, device_id),
            )
        if push_token is not None:
            await db.execute(
                "UPDATE devices SET push_token = ?, updated_at = ? WHERE device_id = ?",
                (push_token, now, device_id),
            )
        await db.commit()
    device = await get_device(device_id)
    assert device is not None
    return device


async def count_routes(device_id: str) -> int:
    async with aiosqlite.connect(settings.database_path) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM routes WHERE device_id = ? AND active = 1",
            (device_id,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def list_routes(device_id: str) -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT r.*, ps.price AS last_price, ps.departure_at AS last_departure, "
            "ps.return_at AS last_return, ps.fetched_at AS last_checked "
            "FROM routes r "
            "LEFT JOIN price_snapshots ps ON ps.id = ("
            "  SELECT id FROM price_snapshots WHERE route_id = r.id "
            "  ORDER BY fetched_at DESC LIMIT 1"
            ") "
            "WHERE r.device_id = ? AND r.active = 1 "
            "ORDER BY r.id",
            (device_id,),
        )
        rows = await cur.fetchall()
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
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM routes WHERE device_id = ? AND destination_iata = ? AND active = 1",
            (device_id, dest),
        )
        if await cur.fetchone():
            raise ValueError("Это направление уже добавлено")

        cur = await db.execute(
            "SELECT * FROM routes WHERE device_id = ? AND destination_iata = ? AND active = 0",
            (device_id, dest),
        )
        inactive = await cur.fetchone()
        if inactive:
            await db.execute(
                "UPDATE routes SET active = 1, max_price = ?, label = ?, "
                "destination_country = ?, destination_city = ?, trip_class = ?, departure_month = ?, "
                "departure_date = ?, date_flex_days = ?, one_way = ? WHERE id = ?",
                (
                    max_price,
                    label,
                    destination_country,
                    destination_city,
                    trip_class,
                    departure_month,
                    departure_date,
                    date_flex_days,
                    1 if one_way else 0,
                    inactive["id"],
                ),
            )
            await db.commit()
            cur = await db.execute("SELECT * FROM routes WHERE id = ?", (inactive["id"],))
            row = await cur.fetchone()
            return dict(row)

        try:
            await db.execute(
                "INSERT INTO routes ("
                "device_id, destination_iata, max_price, label, created_at, "
                "destination_country, destination_city, trip_class, departure_month, departure_date, "
                "date_flex_days, one_way"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
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
                    1 if one_way else 0,
                ),
            )
            await db.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError("Это направление уже добавлено") from e
        cur = await db.execute(
            "SELECT * FROM routes WHERE device_id = ? AND destination_iata = ? ORDER BY id DESC LIMIT 1",
            (device_id, dest),
        )
        row = await cur.fetchone()
        return dict(row)


async def delete_route(device_id: str, route_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cur = await db.execute(
            "SELECT id FROM routes WHERE id = ? AND device_id = ?",
            (route_id, device_id),
        )
        if not await cur.fetchone():
            return False
        await db.execute("DELETE FROM alerts_sent WHERE route_id = ?", (route_id,))
        await db.execute("DELETE FROM price_snapshots WHERE route_id = ?", (route_id,))
        cur = await db.execute(
            "DELETE FROM routes WHERE id = ? AND device_id = ?",
            (route_id, device_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_active_routes_for_price_check() -> list[dict]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT r.*, d.origin_iata, d.push_token "
            "FROM routes r "
            "JOIN devices d ON d.device_id = r.device_id "
            "WHERE r.active = 1 AND d.origin_iata IS NOT NULL"
        )
        return [dict(r) for r in await cur.fetchall()]


async def save_snapshot(
    route_id: int,
    price: int,
    departure_at: str | None,
    return_at: str | None,
    airline: str | None,
    link: str | None,
) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO price_snapshots "
            "(route_id, price, departure_at, return_at, airline, link, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (route_id, price, departure_at, return_at, airline, link, _now()),
        )
        await db.commit()


async def get_last_snapshot(route_id: int) -> dict | None:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM price_snapshots WHERE route_id = ? "
            "ORDER BY fetched_at DESC LIMIT 1",
            (route_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_last_alert(route_id: int) -> dict | None:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM alerts_sent WHERE route_id = ? ORDER BY sent_at DESC LIMIT 1",
            (route_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def record_alert(route_id: int, price: int) -> None:
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO alerts_sent (route_id, price, sent_at) VALUES (?, ?, ?)",
            (route_id, price, _now()),
        )
        await db.commit()
