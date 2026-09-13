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


def test_api_segments_withholds_inventory_on_fatal_finding() -> None:
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000001*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "GE*1*1~IEA*2*000000001~"  # IEA01 overstates the group count -- fatal
    )
    response = client.post("/api/segments", json={"edi": edi})
    assert response.status_code == 200
    interchange = response.json()["interchanges"][0]
    assert interchange["recovered"] is True
    assert interchange["has_fatal"] is True
    assert interchange["inventory"] is None


def test_segments_page_lists_every_sample() -> None:
    from x12_tools.samples import SAMPLES

    response = client.get("/segments")
    assert response.status_code == 200
    for sample in SAMPLES:
        assert sample.title in response.text
        assert sample.slug in response.text
