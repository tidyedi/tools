# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

from fastapi.testclient import TestClient

from x12_tools.app import app

client = TestClient(app)


def test_index_lists_the_segments_tool() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Segment inventory" in response.text


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_segments_happy_path(two_orders_edi: str) -> None:
    response = client.post("/api/segments", json={"edi": two_orders_edi})
    assert response.status_code == 200
    data = response.json()
    assert data["interchange_count"] == 1
    interchange = data["interchanges"][0]
    assert interchange["was_clean"] is True
    assert interchange["inventory"]["transaction_sets"][0]["transaction_set_id"] == "850"


def test_api_segments_rejects_empty_input() -> None:
    response = client.post("/api/segments", json={"edi": "   "})
    assert response.status_code == 422
    assert "detail" in response.json()
