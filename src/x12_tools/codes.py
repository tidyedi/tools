# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""List the distinct values seen in every element -- e.g. every value that
showed up in N101, every REF01 qualifier, every BEG03 purchase order number
-- alongside that element's definition (name, requirement, data type,
length), grouped by transaction set type, the same way
:mod:`x12_tools.inventory` groups segments.

This is deliberately just the *inventory* half of "identify codes we don't
have in our convention": it says what values actually showed up in the
file, per element position, so they can be read off or exported. Comparing
that against an accepted list -- flagging what's new -- is a separate step,
not implemented here yet, since what "our convention" is checked against (a
list built up over time, the official X12 code list, a pasted reference) is
still an open question. This module produces the input either approach
would need.

Every position defined in :data:`x12_tools.element_definitions.SEGMENT_ELEMENTS`
is looked at, regardless of its ``data_type`` -- a free-text or numeric
element's "values found" is just as useful a starting point as a coded
one's. A segment or position not in that reference is simply not covered
yet, the same "blank means not covered" contract as
:mod:`x12_tools.segment_names`.

Built on x12-tidy's own mechanical segment/element split
(:mod:`x12_tidy.envelope.structure`) -- nothing here validates or judges the
interchange; that already happened in the cleanse step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from x12_tidy.envelope.isa import extract_isa_line, split_isa_line
from x12_tidy.envelope.structure import drop_null_rows, split_elements, split_segments

from x12_tools.element_definitions import SEGMENT_ELEMENTS, ElementDefinition

#: Envelope segments that open an interchange/functional group, in the order
#: they appear ahead of any transaction set's own content. Mirrors
#: :mod:`x12_tools.inventory`'s split of the same envelope.
_ENVELOPE_HEADER = ("ISA", "GS")
#: Envelope segments that close a functional group/interchange, in the order
#: they appear after every transaction set's own content.
_ENVELOPE_TRAILER = ("GE", "IEA")

#: segment_id -> {position -> definition}, every defined element -- computed
#: once from SEGMENT_ELEMENTS rather than maintained as a second, separate
#: reference that could drift from it.
_ELEMENTS_BY_SEGMENT: dict[str, dict[int, ElementDefinition]] = {
    segment_id: {e.position: e for e in elements} for segment_id, elements in SEGMENT_ELEMENTS.items()
}


@dataclass(frozen=True)
class ElementCodes:
    """One element's definition, plus every distinct value seen at that
    position, in first-appearance order, across every occurrence."""

    segment_id: str
    position: int  # 1-based, matching X12's own element numbering
    name: str
    requirement: str  # this element's own M/O/C within the segment
    min_length: int
    max_length: int
    values: list[str]
    #: One raw segment (as its decoded, delimiter-joined tokens -- segment ID
    #: first, then every data element) per entry in ``values``, same index --
    #: an actual occurrence that carried that value, for on-screen context.
    raw_segments: list[list[str]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "position": self.position,
            "name": self.name,
            "requirement": self.requirement,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "values": self.values,
            "raw_segments": self.raw_segments,
        }


@dataclass(frozen=True)
class TransactionSetCodes:
    """One transaction set type's element inventory -- envelope header
    (ISA/GS) first, this type's own body second, envelope trailer (GE/IEA)
    last -- the same ``ISA, GS, ST, ..., SE, GE, IEA`` order as
    :mod:`x12_tools.inventory`."""

    transaction_set_id: str
    releases: list[str]
    codes: list[ElementCodes]

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_set_id": self.transaction_set_id,
            "releases": self.releases,
            "codes": [c.as_dict() for c in self.codes],
        }


@dataclass(frozen=True)
class CodeInventory:
    """One interchange's element inventory."""

    transaction_sets: list[TransactionSetCodes]
    #: This interchange's own element separator (ISA16 in modern X12, or
    #: whatever x12-tidy recovered) -- how the page joins a row's
    #: ``raw_segments`` tokens back into the segment string it displays.
    separator: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_sets": [ts.as_dict() for ts in self.transaction_sets],
            "separator": self.separator,
        }


@dataclass
class _CodeGroup:
    values: dict[tuple[str, int], list[str]] = field(default_factory=dict)
    raw_segments: dict[tuple[str, int], list[list[str]]] = field(default_factory=dict)
    seen: dict[tuple[str, int], set[str]] = field(default_factory=dict)
    order: list[tuple[str, int]] = field(default_factory=list)
    releases: list[str] = field(default_factory=list)
    seen_releases: set[str] = field(default_factory=set)

    def add(self, segment_id: str, elements: tuple[bytes, ...]) -> None:
        tokens: list[str] | None = None
        for position in _ELEMENTS_BY_SEGMENT.get(segment_id, {}):
            if position > len(elements):
                continue
            value = elements[position - 1].decode("ascii", errors="replace").strip()
            if not value:
                continue
            key = (segment_id, position)
            if key not in self.seen:
                self.seen[key] = set()
                self.values[key] = []
                self.raw_segments[key] = []
                self.order.append(key)
            if value not in self.seen[key]:
                if tokens is None:
                    # Built lazily, once per occurrence, and shared across
                    # every position that finds a new value in it.
                    tokens = [segment_id] + [
                        e.decode("ascii", errors="replace").strip() for e in elements
                    ]
                self.seen[key].add(value)
                self.values[key].append(value)
                self.raw_segments[key].append(tokens)

    def add_release(self, release: str) -> None:
        if release and release not in self.seen_releases:
            self.seen_releases.add(release)
            self.releases.append(release)

    def entries(self) -> list[ElementCodes]:
        # SE always closes a transaction set, so -- same reasoning as
        # :meth:`x12_tools.inventory._Group.entries` -- it's forced to the
        # end of the body rather than trusted to first-appearance order,
        # which a later occurrence introducing a new segment type could
        # otherwise push SE ahead of.
        keys = [key for key in self.order if key[0] != "SE"]
        keys.extend(key for key in self.order if key[0] == "SE")
        entries = []
        for sid, pos in keys:
            definition = _ELEMENTS_BY_SEGMENT[sid][pos]
            entries.append(
                ElementCodes(
                    sid,
                    pos,
                    definition.name,
                    definition.requirement,
                    definition.min_length,
                    definition.max_length,
                    self.values[(sid, pos)],
                    self.raw_segments[(sid, pos)],
                )
            )
        return entries


def build_code_inventory(payload: bytes) -> CodeInventory:
    """Walk one cleansed interchange's bytes and collect every defined
    element's values, grouped the same way as :func:`x12_tools.inventory.build_inventory`.

    ``payload`` must be the reconstructed bytes x12-tidy handed back -- the
    same bytes :func:`x12_tools.engine.cleanse` exposes as ``CleanResult.payload``.
    """
    located = extract_isa_line(payload)
    if located.isa_line is None:
        return CodeInventory([], "")

    decomposition = split_isa_line(located.isa_line, base_offset=located.isa_start)
    element_separator = decomposition.element_separator
    if not element_separator:
        return CodeInventory([], "")

    segments = drop_null_rows(split_segments(payload))

    envelope = _CodeGroup()
    if decomposition.elements:
        envelope.add("ISA", decomposition.elements)
    groups: dict[str, _CodeGroup] = {}
    group_order: list[str] = []
    current_ts_id: str | None = None
    current_release = ""

    for segment in segments:
        elements = split_elements(segment, element_separator)
        segment_id = elements[0].decode("ascii", errors="replace")
        data_elements = tuple(elements[1:])

        if segment_id == "GS":
            current_release = (
                data_elements[7].decode("ascii", errors="replace").strip()
                if len(data_elements) > 7
                else ""
            )
            envelope.add(segment_id, data_elements)
            continue

        if segment_id == "ST":
            current_ts_id = (
                data_elements[0].decode("ascii", errors="replace") if data_elements else "UNKNOWN"
            )
            group = groups.setdefault(current_ts_id, _CodeGroup())
            if current_ts_id not in group_order:
                group_order.append(current_ts_id)
            group.add(segment_id, data_elements)
            group.add_release(current_release)
            continue

        if current_ts_id is not None:
            groups[current_ts_id].add(segment_id, data_elements)
            if segment_id == "SE":
                current_ts_id = None
        else:
            envelope.add(segment_id, data_elements)

    envelope_entries = {(e.segment_id, e.position): e for e in envelope.entries()}
    header = [e for e in envelope_entries.values() if e.segment_id in _ENVELOPE_HEADER]
    trailer = [e for e in envelope_entries.values() if e.segment_id in _ENVELOPE_TRAILER]
    transaction_sets = [
        TransactionSetCodes(ts_id, groups[ts_id].releases, header + groups[ts_id].entries() + trailer)
        for ts_id in group_order
    ]
    return CodeInventory(transaction_sets, element_separator.decode("ascii", errors="replace"))
