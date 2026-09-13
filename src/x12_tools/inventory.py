# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""List the unique segments a cleansed interchange contains, grouped by
transaction set type -- a starting point for writing an implementation
convention / companion guide.

An interchange can carry several transaction sets, and a batch can repeat the
same type many times (e.g. a hundred ``837`` claims in one functional group).
A companion guide is written per transaction set *type* (ST01, e.g. ``837``)
at a given release (GS08, e.g. ``004010``), so occurrences of the same type
are merged into one list. ``ISA``, ``GS``, ``GE`` and ``IEA`` are envelope
segments, not transaction-set content, but they are still segments that show
up around every transaction set's own -- so each type's list is the envelope
segments (``ISA``/``GS`` first, ``GE``/``IEA`` last) plus everything seen
inside any ``ST``..``SE`` loop of that type, deduplicated, in first-appearance
order within each part.

Each entry also carries an element count: the most elements x12-tidy saw
after that segment's identifier in any occurrence within the group. A
convention needs to know how many elements a segment actually carries, not
just that it showed up; taking the max (rather than, say, the first
occurrence's count) means an optional trailing element that's only populated
some of the time still gets counted.

Built on x12-tidy's own mechanical segment/element split
(:mod:`x12_tidy.envelope.structure`) -- nothing here validates or judges the
interchange; that already happened in the cleanse step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from x12_tidy.envelope.isa import extract_isa_line, split_isa_line
from x12_tidy.envelope.structure import drop_null_rows, split_elements, split_segments

#: Envelope segments that open an interchange/functional group, in the order
#: they appear ahead of any transaction set's own content.
_ENVELOPE_HEADER = ("ISA", "GS")
#: Envelope segments that close a functional group/interchange, in the order
#: they appear after every transaction set's own content.
_ENVELOPE_TRAILER = ("GE", "IEA")
#: ISA is a fixed-format segment -- always exactly ISA01..ISA16, regardless of
#: release -- and it never appears in x12-tidy's segment split (which starts
#: at GS), so its element count is a constant rather than something walked.
_ISA_ELEMENT_COUNT = 16


@dataclass(frozen=True)
class SegmentEntry:
    """One segment ID and how many elements it carries, at most, across every
    occurrence seen."""

    segment_id: str
    element_count: int

    def as_dict(self) -> dict[str, Any]:
        return {"segment_id": self.segment_id, "element_count": self.element_count}


@dataclass(frozen=True)
class TransactionSetSegments:
    """The unique segments seen across every occurrence of one transaction set
    type (ST01) -- envelope segments plus this type's own content."""

    transaction_set_id: str  # ST01, e.g. "837"
    #: GS08 (version/release/industry ID) of every functional group this
    #: transaction set type was seen in, in first-seen order. Usually one
    #: value; more than one means the same type showed up under different
    #: releases in this submission.
    releases: list[str]
    segments: list[SegmentEntry]

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_set_id": self.transaction_set_id,
            "releases": self.releases,
            "segments": [s.as_dict() for s in self.segments],
        }


@dataclass(frozen=True)
class SegmentInventory:
    """One interchange's segment inventory."""

    transaction_sets: list[TransactionSetSegments]

    def as_dict(self) -> dict[str, Any]:
        return {"transaction_sets": [ts.as_dict() for ts in self.transaction_sets]}


@dataclass
class _Group:
    segments: list[str] = field(default_factory=list)
    element_counts: dict[str, int] = field(default_factory=dict)
    releases: list[str] = field(default_factory=list)
    seen_releases: set[str] = field(default_factory=set)

    def add(self, segment_id: str, element_count: int) -> None:
        if segment_id not in self.element_counts:
            self.segments.append(segment_id)
        self.element_counts[segment_id] = max(self.element_counts.get(segment_id, 0), element_count)

    def add_release(self, release: str) -> None:
        if release and release not in self.seen_releases:
            self.seen_releases.add(release)
            self.releases.append(release)

    def entries(self) -> list[SegmentEntry]:
        return [SegmentEntry(sid, self.element_counts[sid]) for sid in self.segments]


def build_inventory(payload: bytes) -> SegmentInventory:
    """Walk one cleansed interchange's bytes and group its segments.

    ``payload`` must be the reconstructed bytes x12-tidy handed back (a full
    ``ISA``..``IEA`` interchange) -- the same bytes :func:`x12_tools.engine.cleanse`
    exposes as ``CleanResult.payload``.
    """
    located = extract_isa_line(payload)
    if located.isa_line is None:
        return SegmentInventory([])

    decomposition = split_isa_line(located.isa_line, base_offset=located.isa_start)
    element_separator = decomposition.element_separator
    if not element_separator:
        return SegmentInventory([])

    # split_segments starts at GS (the ISA line is a separate, upstream
    # concern) -- so ISA is folded in explicitly, with its fixed element count.
    segments = drop_null_rows(split_segments(payload))

    envelope = _Group()
    envelope.add("ISA", _ISA_ELEMENT_COUNT)
    groups: dict[str, _Group] = {}
    group_order: list[str] = []
    current_ts_id: str | None = None
    current_release = ""  # GS08 of the functional group currently open

    for segment in segments:
        elements = split_elements(segment, element_separator)
        segment_id = elements[0].decode("ascii", errors="replace")
        element_count = len(elements) - 1  # elements[0] is the identifier, not a data element

        if segment_id == "GS":
            current_release = (
                elements[8].decode("ascii", errors="replace").strip() if len(elements) > 8 else ""
            )
            envelope.add(segment_id, element_count)
            continue

        if segment_id == "ST":
            current_ts_id = (
                elements[1].decode("ascii", errors="replace") if len(elements) > 1 else "UNKNOWN"
            )
            group = groups.setdefault(current_ts_id, _Group())
            if current_ts_id not in group_order:
                group_order.append(current_ts_id)
            group.add(segment_id, element_count)
            group.add_release(current_release)
            continue

        if current_ts_id is not None:
            groups[current_ts_id].add(segment_id, element_count)
            if segment_id == "SE":
                current_ts_id = None
        else:
            envelope.add(segment_id, element_count)

    envelope_entries = {e.segment_id: e for e in envelope.entries()}
    header = [envelope_entries[s] for s in _ENVELOPE_HEADER if s in envelope_entries]
    trailer = [envelope_entries[s] for s in _ENVELOPE_TRAILER if s in envelope_entries]

    transaction_sets = [
        TransactionSetSegments(ts_id, groups[ts_id].releases, header + groups[ts_id].entries() + trailer)
        for ts_id in group_order
    ]
    return SegmentInventory(transaction_sets)
