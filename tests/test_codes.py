# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

from x12_tools.codes import ElementCodes, build_code_inventory
from x12_tools.engine import cleanse


def _codes(entries: list[ElementCodes]) -> dict[tuple[str, int], list[str]]:
    return {(c.segment_id, c.position): c.values for c in entries}


def test_envelope_codes_are_folded_into_the_transaction_sets_codes(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    assert len(inventory.transaction_sets) == 1
    codes = _codes(inventory.transaction_sets[0].codes)
    # ISA05/ISA07 (interchange ID qualifiers) and ISA01/ISA03 (auth/security
    # qualifiers) are ID-type and covered by element_definitions.py.
    assert codes[("ISA", 5)] == ["ZZ"]
    assert codes[("ISA", 1)] == ["00"]
    # GS01 (functional ID code) is covered too.
    assert codes[("GS", 1)] == ["PO"]


def test_distinct_values_across_occurrences_are_merged_in_first_seen_order() -> None:
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

    codes = _codes(inventory.transaction_sets[0].codes)
    # N101 (entity identifier code): "ST" seen in both occurrences (not
    # duplicated), "BT" only in the second -- first-appearance order overall.
    assert codes[("N1", 1)] == ["ST", "BT"]
    # BEG01/BEG02 (transaction set purpose / PO type codes) are identical
    # across both occurrences, so just one value each.
    assert codes[("BEG", 1)] == ["00"]
    assert codes[("BEG", 2)] == ["NE"]


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

    codes = _codes(inventory.transaction_sets[0].codes)
    assert codes[("CTT", 1)] == ["1"]


def test_envelope_trailer_sorts_after_the_transaction_sets_own_segments() -> None:
    # GE/IEA close the interchange on the wire, after SE -- the merged list
    # must keep that order (ISA, GS, ..., SE, GE, IEA), not lump every
    # envelope segment together up front just because ISA/GS were seen
    # first in the file.
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        "240101*1200*U*00401*000000008*0*P*:~"
        "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
        "ST*850*0001~BEG*00*NE*PO0001**20240101~SE*3*0001~"
        "GE*1*1~IEA*1*000000008~"
    )
    result = cleanse(edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    order = [c.segment_id for c in inventory.transaction_sets[0].codes]
    assert order.index("SE") < order.index("GE") < order.index("IEA")
    assert order.index("BEG") < order.index("SE")


def test_raw_segments_carry_one_occurrence_per_distinct_value(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    assert inventory.separator == "*"
    by_key = {(c.segment_id, c.position): c for c in inventory.transaction_sets[0].codes}
    gs01 = by_key[("GS", 1)]
    assert len(gs01.raw_segments) == len(gs01.values) == 1
    # The raw segment is the decoded, un-split GS occurrence -- segment ID
    # first, then every data element -- so the value at this position lines
    # up with the element at the same index.
    raw = gs01.raw_segments[0]
    assert raw[0] == "GS"
    assert raw[1] == gs01.values[0]


def test_unrecoverable_input_yields_empty_inventory() -> None:
    inventory = build_code_inventory(b"not an EDI file at all")
    assert inventory.transaction_sets == []


def test_element_definition_fields_are_attached_to_each_code(two_orders_edi: str) -> None:
    result = cleanse(two_orders_edi)[0]
    assert result.payload is not None
    inventory = build_code_inventory(result.payload)

    by_key = {(c.segment_id, c.position): c for c in inventory.transaction_sets[0].codes}
    gs01 = by_key[("GS", 1)]
    assert gs01.name == "Functional Identifier Code"
    assert gs01.requirement == "M"
    assert gs01.min_length == 2
    assert gs01.max_length == 2
