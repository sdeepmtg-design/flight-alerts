"""Render Cron Job: POST /internal/check-prices на web-сервисе."""
import os
import sys

import httpx

host = os.environ.get("API_HOST", "").strip()
secret = os.environ.get("CRON_SECRET", "").strip()

if not host or not secret:
    print("API_HOST и CRON_SECRET обязательны", file=sys.stderr)
    sys.exit(1)

url = f"https://{host}/internal/check-prices?secret={secret}"
print(f"POST {url.split('?')[0]}")

with httpx.Client(timeout=180.0) as client:
    response = client.post(url)
    response.raise_for_status()
    print(response.json())
