# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

from x12_tools.engine import cleanse
from x12_tools.inventory import build_inventory


def test_envelope_segments_are_folded_into_each_transaction_sets_list(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)

    assert len(inventory.transaction_sets) == 1
    ts = inventory.transaction_sets[0]
    # ISA/GS lead, GE/IEA trail -- x12-tidy's split_segments starts at GS (the
    # ISA line is a separate, upstream concern), so ISA is added back
    # explicitly; the rest come from walking segments outside any ST..SE loop.
    assert ts.segments[:2] == ["ISA", "GS"]
    assert ts.segments[-2:] == ["GE", "IEA"]


def test_two_occurrences_of_same_transaction_set_are_merged(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)

    assert len(inventory.transaction_sets) == 1
    ts = inventory.transaction_sets[0]
    assert ts.transaction_set_id == "850"
    # First occurrence contributes ST, BEG, N1, SE; the second adds PO1 (not
    # already seen) but repeats ST/BEG/SE without duplicating them. Envelope
    # segments (ISA/GS header, GE/IEA trailer) are folded around them.
    assert ts.segments == ["ISA", "GS", "ST", "BEG", "N1", "SE", "PO1", "GE", "IEA"]
    assert ts.releases == ["004010"]


def test_distinct_transaction_set_types_get_separate_lists() -> None:
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000002*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*2*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "ST*855*0002~BAK*00*AC*PO0001**20240101~SE*3*0002~"
        "GE*1*2~IEA*1*000000002~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)

    ids = [ts.transaction_set_id for ts in inventory.transaction_sets]
    assert ids == ["850", "855"]
    assert inventory.transaction_sets[0].segments == ["ISA", "GS", "ST", "BEG", "SE", "GE", "IEA"]
    assert inventory.transaction_sets[1].segments == ["ISA", "GS", "ST", "BAK", "SE", "GE", "IEA"]
    assert inventory.transaction_sets[0].releases == ["004010"]
    assert inventory.transaction_sets[1].releases == ["004010"]


def test_same_transaction_set_type_across_two_releases_lists_both() -> None:
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000003*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "GE*1*1~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*2*X*005010~"
        "ST*850*0002~BEG*00*NE*PO0002**20240101~SE*3*0002~"
        "GE*1*2~"
        "IEA*2*000000003~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)

    assert len(inventory.transaction_sets) == 1
    ts = inventory.transaction_sets[0]
    assert ts.releases == ["004010", "005010"]
    assert ts.segments == ["ISA", "GS", "ST", "BEG", "SE", "GE", "IEA"]
