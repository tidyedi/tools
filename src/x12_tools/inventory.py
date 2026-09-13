# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""List the unique segments a cleansed interchange contains, grouped by
transaction set type -- a starting point for writing an implementation
convention / companion guide.

An interchange can carry several transaction sets, and a batch can repeat the
same type many times (e.g. a hundred ``837`` claims in one functional group).
A companion guide is written per transaction set *type* (ST01, e.g. ``837``),
not per occurrence, so occurrences of the same type are merged: the result is
the set of distinct segment IDs seen anywhere inside any ``ST``..``SE`` loop of
that type, in first-appearance order. Segments outside every ``ST``..``SE``
loop (``ISA``, ``GS``, ``GE``, ``IEA``, and anything else at the envelope
level) are reported separately, since they aren't part of any transaction
set's own convention.

Built on x12-tidy's own mechanical segment/element split
(:mod:`x12_tidy.envelope.structure`) -- nothing here validates or judges the
interchange; that already happened in the cleanse step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from x12_tidy.envelope.isa import extract_isa_line, split_isa_line
from x12_tidy.envelope.structure import drop_null_rows, split_elements, split_segments


@dataclass(frozen=True)
class TransactionSetSegments:
    """The unique segments seen across every occurrence of one transaction set
    type (ST01), in first-appearance order."""

    transaction_set_id: str  # ST01, e.g. "837"
    occurrences: int  # how many ST..SE loops of this type were found
    segments: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_set_id": self.transaction_set_id,
            "occurrences": self.occurrences,
            "segments": self.segments,
        }


@dataclass(frozen=True)
class SegmentInventory:
    """One interchange's segment inventory."""

    envelope_segments: list[str]
    transaction_sets: list[TransactionSetSegments]

    def as_dict(self) -> dict[str, Any]:
        return {
            "envelope_segments": self.envelope_segments,
            "transaction_sets": [ts.as_dict() for ts in self.transaction_sets],
        }


@dataclass
class _Group:
    occurrences: int = 0
    segments: list[str] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)

    def add(self, segment_id: str) -> None:
        if segment_id not in self.seen:
            self.seen.add(segment_id)
            self.segments.append(segment_id)


def build_inventory(payload: bytes) -> SegmentInventory:
    """Walk one cleansed interchange's bytes and group its segments.

    ``payload`` must be the reconstructed bytes x12-tidy handed back (a full
    ``ISA``..``IEA`` interchange) -- the same bytes :func:`x12_tools.engine.cleanse`
    exposes as ``CleanResult.payload``.
    """
    located = extract_isa_line(payload)
    if located.isa_line is None:
        return SegmentInventory([], [])

    decomposition = split_isa_line(located.isa_line, base_offset=located.isa_start)
    element_separator = decomposition.element_separator
    if not element_separator:
        return SegmentInventory([], [])

    segments = drop_null_rows(split_segments(payload))

    envelope = _Group()
    groups: dict[str, _Group] = {}
    group_order: list[str] = []
    current_ts_id: str | None = None

    for segment in segments:
        elements = split_elements(segment, element_separator)
        segment_id = elements[0].decode("ascii", errors="replace")

        if segment_id == "ST":
            current_ts_id = (
                elements[1].decode("ascii", errors="replace") if len(elements) > 1 else "UNKNOWN"
            )
            group = groups.setdefault(current_ts_id, _Group())
            if current_ts_id not in group_order:
                group_order.append(current_ts_id)
            group.occurrences += 1
            group.add(segment_id)
            continue

        if current_ts_id is not None:
            groups[current_ts_id].add(segment_id)
            if segment_id == "SE":
                current_ts_id = None
        else:
            envelope.add(segment_id)

    transaction_sets = [
        TransactionSetSegments(ts_id, groups[ts_id].occurrences, groups[ts_id].segments)
        for ts_id in group_order
    ]
    return SegmentInventory(envelope.segments, transaction_sets)
