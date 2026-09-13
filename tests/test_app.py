# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

import pytest
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


def test_index_lists_the_codes_tool() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Code inventory" in response.text


def test_api_codes_happy_path(two_orders_edi: str) -> None:
    response = client.post("/api/codes", json={"edi": two_orders_edi})
    assert response.status_code == 200
    data = response.json()
    codes = data["interchanges"][0]["inventory"]["transaction_sets"][0]["codes"]
    gs01 = next(c for c in codes if c["segment_id"] == "GS" and c["position"] == 1)
    assert gs01["values"] == ["PO"]
    assert gs01["name"] == "Functional Identifier Code"


def test_api_codes_withholds_inventory_on_fatal_finding() -> None:
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000001*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "GE*1*1~IEA*2*000000001~"  # IEA01 overstates the group count -- fatal
    )
    response = client.post("/api/codes", json={"edi": edi})
    assert response.status_code == 200
    interchange = response.json()["interchanges"][0]
    assert interchange["has_fatal"] is True
    assert interchange["inventory"] is None


def test_codes_page_loads() -> None:
    response = client.get("/codes")
    assert response.status_code == 200
    assert "Code inventory" in response.text


def test_reference_page_lists_known_segments_and_elements() -> None:
    response = client.get("/reference")
    assert response.status_code == 200
    assert "Interchange Control Header" in response.text  # ISA, from segment_names.py
    assert "Functional Identifier Code" in response.text  # GS01, from element_definitions.py


def test_segments_and_codes_pages_link_to_reference() -> None:
    for path in ("/segments", "/codes"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'href="/reference"' in response.text


def test_convention_page_loads() -> None:
    response = client.get("/convention")
    assert response.status_code == 200
    assert "Convention importer" in response.text


def test_api_convention_rejects_non_pdf_filename() -> None:
    response = client.post("/api/convention", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 422


def test_api_convention_rejects_empty_file() -> None:
    response = client.post("/api/convention", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert response.status_code == 422


def test_api_convention_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from x12_tools import app as app_module
    from x12_tools.convention_pdf import ConventionSegmentRow, ParsedConvention

    canned = ParsedConvention(
        segment_table=[
            ConventionSegmentRow("10", None, "ST", "Transaction Set Header", "M", "1", "", "", "Must use", False)
        ],
        segment_details={},
    )
    monkeypatch.setattr(app_module, "parse_convention_pdf", lambda data: canned)

    response = client.post("/api/convention", files={"file": ("ic.pdf", b"%PDF-fake", "application/pdf")})
    assert response.status_code == 200
    data = response.json()
    assert data["segment_table"][0]["segment_id"] == "ST"


def test_api_convention_reports_missing_pdftotext(monkeypatch: pytest.MonkeyPatch) -> None:
    from x12_tools import app as app_module
    from x12_tools.convention_pdf import PdftotextMissing

    def raise_missing(data: bytes) -> None:
        raise PdftotextMissing("pdftotext (poppler) is not installed on this server")

    monkeypatch.setattr(app_module, "parse_convention_pdf", raise_missing)

    response = client.post("/api/convention", files={"file": ("ic.pdf", b"%PDF-fake", "application/pdf")})
    assert response.status_code == 503
    assert "poppler" in response.json()["detail"]
