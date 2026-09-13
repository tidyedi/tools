# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

from x12_tools.engine import cleanse
from x12_tools.inventory import SegmentEntry, build_inventory


def _ids(entries: list[SegmentEntry]) -> list[str]:
    return [e.segment_id for e in entries]


def _counts(entries: list[SegmentEntry]) -> dict[str, int]:
    return {e.segment_id: e.element_count for e in entries}


def _populated(entries: list[SegmentEntry]) -> dict[str, int]:
    return {e.segment_id: e.populated_count for e in entries}


def test_envelope_segments_are_folded_into_each_transaction_sets_list(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)

    assert len(inventory.transaction_sets) == 1
    ts = inventory.transaction_sets[0]
    # ISA/GS lead, GE/IEA trail -- x12-tidy's split_segments starts at GS (the
    # ISA line is a separate, upstream concern), so ISA is added back
    # explicitly; the rest come from walking segments outside any ST..SE loop.
    ids = _ids(ts.segments)
    assert ids[:2] == ["ISA", "GS"]
    assert ids[-2:] == ["GE", "IEA"]

    counts = _counts(ts.segments)
    assert counts["ISA"] == 16  # fixed -- ISA01..ISA16, never walked
    assert counts["GS"] == 8  # PO, SENDERGS, RECEIVERID, 20240101, 1200, 1, X, 004010

    populated = _populated(ts.segments)
    assert populated["GS"] == 8  # none of GS's elements are blank here
    # ISA02 and ISA04 are the space-padded "authorization/security information"
    # values -- blank because ISA01/ISA03 are "00" (none present) -- so 14 of
    # ISA's 16 fixed elements actually carry a value in this fixture.
    assert populated["ISA"] == 14


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
    assert _ids(ts.segments) == ["ISA", "GS", "ST", "BEG", "N1", "SE", "PO1", "GE", "IEA"]
    assert ts.releases == ["004010"]


def test_populated_count_excludes_blank_elements(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)
    ts = inventory.transaction_sets[0]

    counts = _counts(ts.segments)
    populated = _populated(ts.segments)
    # BEG*00*NE*PO0001**20240101 -- 5 elements, but the 4th (between PO0001 and
    # the date) is empty in both occurrences.
    assert counts["BEG"] == 5
    assert populated["BEG"] == 4
    # N1*ST*Warehouse -- both elements populated, nothing to exclude.
    assert counts["N1"] == populated["N1"] == 2


def test_populated_count_is_a_union_across_occurrences() -> None:
    # Occurrence 1 leaves position 4 blank; occurrence 2 fills it in. The
    # position should count as populated overall -- it's used at least once,
    # even though a single occurrence never shows both facts at once.
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000005*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "ST*850*0002~BEG*00*NE*PO0002*RUSH*20240101~SE*3*0002~"
        "GE*2*1~IEA*1*000000005~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)

    populated = _populated(inventory.transaction_sets[0].segments)
    assert populated["BEG"] == 5  # all 5 positions were populated in at least one occurrence


def test_element_count_is_the_max_seen_across_occurrences() -> None:
    # BEG carries 5 elements (incl. one empty) in both occurrences here, but a
    # second occurrence with a longer BEG should raise the recorded count.
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000004*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "ST*850*0002~BEG*00*NE*PO0002**20240101*EXTRA~SE*3*0002~"
        "GE*2*1~IEA*1*000000004~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_inventory(result.payload)

    counts = _counts(inventory.transaction_sets[0].segments)
    assert counts["BEG"] == 6  # the second occurrence's extra trailing element wins


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
    assert _ids(inventory.transaction_sets[0].segments) == ["ISA", "GS", "ST", "BEG", "SE", "GE", "IEA"]
    assert _ids(inventory.transaction_sets[1].segments) == ["ISA", "GS", "ST", "BAK", "SE", "GE", "IEA"]
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
    assert _ids(ts.segments) == ["ISA", "GS", "ST", "BEG", "SE", "GE", "IEA"]
