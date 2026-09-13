# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

from x12_tools.engine import cleanse


def test_cleanse_conformant_input_is_clean(two_orders_edi: str) -> None:
    results = cleanse(two_orders_edi)
    assert len(results) == 1
    result = results[0]
    assert result.recovered
    assert result.was_clean
    assert result.diagnostics == []
    assert result.payload is not None
    assert result.has_fatal is False


def test_has_fatal_true_when_a_fatal_finding_survives_repair() -> None:
    # IEA01 overstates the functional-group count -- x12-tidy repairs the ISA
    # line but reports this rather than guessing a fix; it's fatal because a
    # conforming receiver would reject the interchange over it.
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000001*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "GE*1*1~IEA*2*000000001~"
    )
    result = cleanse(edi)[0]
    assert result.recovered  # an ISA line was located and a payload produced
    assert result.payload is not None
    assert result.has_fatal is True


def test_cleanse_exposes_sender_receiver_and_version(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.facts is not None
    assert result.facts.sender_qualifier == "ZZ"
    assert result.facts.sender_id == "SENDER"
    assert result.facts.receiver_qualifier == "ZZ"
    assert result.facts.receiver_id == "RECEIVER"
    assert result.facts.interchange_version == "00401"
    assert result.facts.group_versions == ["004010"]
    assert result.facts.interchange_date == "2024-01-01"  # ISA09 "240101" -> ISO, assuming 20xx


def test_cleanse_unrecoverable_input() -> None:
    results = cleanse("not an EDI file at all")
    assert len(results) == 1
    assert results[0].recovered is False
    assert results[0].payload is None
    assert results[0].cleansed_text is None
