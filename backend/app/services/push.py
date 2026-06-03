import httpx

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_expo_push(token: str, title: str, body: str, data: dict | None = None) -> bool:
    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            EXPO_PUSH_URL,
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        if r.status_code != 200:
            return False
        result = r.json()
        if isinstance(result, dict) and result.get("data"):
            status = result["data"].get("status")
            return status == "ok"
        if isinstance(result, list) and result:
            return result[0].get("status") == "ok"
    return True
