# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

from x12_tools.codes import ElementOccurrence, build_code_inventory
from x12_tools.engine import cleanse


def _by_segment(occurrences: list[ElementOccurrence]) -> list[str]:
    return [o.segment_id for o in occurrences]


def test_every_occurrence_gets_its_own_row_not_merged(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    # ISA05/ISA07 (interchange ID qualifiers) and ISA01/ISA03 (auth/security
    # qualifiers) are covered by element_definitions.py.
    isa5 = [o for o in inventory.occurrences if o.segment_id == "ISA" and o.position == 5]
    assert [o.value for o in isa5] == ["ZZ"]
    gs1 = [o for o in inventory.occurrences if o.segment_id == "GS" and o.position == 1]
    assert [o.value for o in gs1] == ["PO"]


def test_repeated_occurrences_are_not_deduplicated() -> None:
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000006*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~N1*ST*Warehouse A~SE*4*0001~"
        "ST*850*0002~BEG*00*NE*PO0002**20240101~N1*BT*HQ~N1*ST*Warehouse B~SE*5*0002~"
        "GE*2*1~IEA*1*000000006~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    # N101 (entity identifier code): every occurrence gets its own row, in
    # file order -- "ST" repeats across both transactions rather than
    # collapsing to one row, and the middle "BT" from the second
    # transaction sits between them in the right spot.
    n1_values = [o.value for o in inventory.occurrences if o.segment_id == "N1" and o.position == 1]
    assert n1_values == ["ST", "BT", "ST"]

    # BEG01 also appears twice -- once per transaction -- not merged to one.
    beg1_values = [o.value for o in inventory.occurrences if o.segment_id == "BEG" and o.position == 1]
    assert beg1_values == ["00", "00"]


def test_true_file_order_is_preserved_across_transactions() -> None:
    # The core guarantee: this table is a literal, in-order parse -- BEG and
    # SE from transaction 1 must appear between transaction 1's ST and
    # transaction 2's ST, never merged or reordered into a per-type grouping.
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000009*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "ST*850*0002~BEG*00*NE*PO0002**20240101~SE*3*0002~"
        "GE*2*1~IEA*1*000000009~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    order = _by_segment(inventory.occurrences)
    first_st = order.index("ST")
    first_se = order.index("SE")
    # ST occupies two consecutive rows (ST01, ST02) -- search past both to
    # find the second transaction's ST, not the first one's own second row.
    second_st = order.index("ST", first_se + 1)
    assert first_st < first_se < second_st
    # BEG of the first transaction sits between its ST and its SE.
    first_beg = order.index("BEG")
    assert first_st < first_beg < first_se


def test_non_id_elements_are_included_too() -> None:
    # CTT has no ID-type elements in element_definitions.py, but it is
    # defined there -- its non-ID elements (CTT01, a count) should still
    # show up. Only segments/positions missing from element_definitions.py
    # entirely are skipped.
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000007*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~CTT*1~SE*4*0001~"
        "GE*1*1~IEA*1*000000007~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    ctt1 = [o for o in inventory.occurrences if o.segment_id == "CTT" and o.position == 1]
    assert [o.value for o in ctt1] == ["1"]


def test_raw_segment_carries_this_occurrences_own_tokens(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    assert inventory.separator == "*"
    gs1 = next(o for o in inventory.occurrences if o.segment_id == "GS" and o.position == 1)
    # The raw segment is this occurrence's own decoded, un-split tokens --
    # segment ID first, then every data element -- so the value at this
    # position lines up with the token at the same index.
    assert gs1.raw_segment[0] == "GS"
    assert gs1.raw_segment[1] == gs1.value


def test_unrecoverable_input_yields_empty_inventory() -> None:
    inventory = build_code_inventory(b"not an EDI file at all")
    assert inventory.occurrences == []


def test_element_definition_fields_are_attached_to_each_occurrence(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    gs1 = next(o for o in inventory.occurrences if o.segment_id == "GS" and o.position == 1)
    assert gs1.name == "Functional Identifier Code"
    assert gs1.requirement == "M"
    assert gs1.min_length == 2
    assert gs1.max_length == 2
