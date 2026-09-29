from __future__ import annotations

import asyncio
import re

import httpx

from app.main import app


def test_request_id_is_generated_and_returned() -> None:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request())

    assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_valid_request_id_is_preserved() -> None:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health", headers={"x-request-id": "req-deadbeef"})

    response = asyncio.run(request())

    assert response.headers["x-request-id"] == "req-deadbeef"
