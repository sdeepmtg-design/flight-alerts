from fastapi import Header, HTTPException

from app import database as db


async def get_device_id(x_device_id: str | None = Header(None, alias="X-Device-Id")) -> str:
    if not x_device_id or len(x_device_id) < 8:
        raise HTTPException(401, "Нужен заголовок X-Device-Id")
    await db.ensure_device(x_device_id)
    return x_device_id
