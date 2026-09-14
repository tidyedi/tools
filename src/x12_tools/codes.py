# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Walk a cleansed interchange segment by segment, in the exact order it
appears on the wire, and emit one row per element occurrence: its value,
its definition (name, requirement, data type, length), and the raw segment
it came from -- with that element's own token identifiable within it.

Deliberately the opposite of :mod:`x12_tools.inventory`: that module
deduplicates repeated segments into a checklist for writing a convention.
This one does not deduplicate or merge anything -- every occurrence of
every element gets its own row, in file order, so a reviewer troubleshooting
a real interchange can answer "where did that value come from?" by reading
straight down the table, the same order the bytes are in.

Every position defined in :data:`x12_tools.element_definitions.SEGMENT_ELEMENTS`
is looked at, regardless of its ``data_type`` -- a free-text or numeric
element's value is just as useful to trace as a coded one's. A segment or
position not in that reference is simply not covered yet, the same "blank
means not covered" contract as :mod:`x12_tools.segment_names`.

Built on x12-tidy's own mechanical segment/element split
(:mod:`x12_tidy.envelope.structure`) -- nothing here validates or judges the
interchange; that already happened in the cleanse step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from x12_tidy.envelope.isa import extract_isa_line, split_isa_line
from x12_tidy.envelope.structure import drop_null_rows, split_elements, split_segments

from x12_tools.element_definitions import SEGMENT_ELEMENTS, ElementDefinition

#: segment_id -> {position -> definition}, every defined element -- computed
#: once from SEGMENT_ELEMENTS rather than maintained as a second, separate
#: reference that could drift from it.
_ELEMENTS_BY_SEGMENT: dict[str, dict[int, ElementDefinition]] = {
    segment_id: {e.position: e for e in elements} for segment_id, elements in SEGMENT_ELEMENTS.items()
}


@dataclass(frozen=True)
class ElementOccurrence:
    """One element, at the exact spot it occurred -- not merged with any
    other occurrence of the same segment/position."""

    segment_id: str
    position: int  # 1-based, matching X12's own element numbering
    name: str
    requirement: str  # this element's own M/O/C within the segment
    min_length: int
    max_length: int
    value: str
    #: This occurrence's raw segment, as its decoded, delimiter-joined
    #: tokens -- segment ID first, then every data element -- so the page
    #: can show the value highlighted in the context it actually came from.
    raw_segment: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "position": self.position,
            "name": self.name,
            "requirement": self.requirement,
            "min_length": self.min_length,
            "max_length": self.max_length,
            "value": self.value,
            "raw_segment": self.raw_segment,
        }


@dataclass(frozen=True)
class CodeInventory:
    """One interchange's element occurrences, in file order."""

    occurrences: list[ElementOccurrence]
    #: This interchange's own element separator (ISA16 in modern X12, or
    #: whatever x12-tidy recovered) -- how the page joins a row's
    #: ``raw_segment`` tokens back into the segment string it displays.
    separator: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "occurrences": [o.as_dict() for o in self.occurrences],
            "separator": self.separator,
        }


def build_code_inventory(payload: bytes) -> CodeInventory:
    """Walk one cleansed interchange's bytes and emit one row per element
    occurrence, in the same order :func:`x12_tools.engine.cleanse` reconstructed
    the bytes in -- no deduplication, no grouping by transaction set type.

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

    occurrences: list[ElementOccurrence] = []

    def emit(segment_id: str, elements: tuple[bytes, ...]) -> None:
        tokens: list[str] | None = None
        for position, definition in _ELEMENTS_BY_SEGMENT.get(segment_id, {}).items():
            if position > len(elements):
                continue
            value = elements[position - 1].decode("ascii", errors="replace").strip()
            if not value:
                continue
            if tokens is None:
                # Built lazily, once per occurrence, and shared across every
                # position this segment carries a value at.
                tokens = [segment_id] + [
                    e.decode("ascii", errors="replace").strip() for e in elements
                ]
            occurrences.append(
                ElementOccurrence(
                    segment_id,
                    position,
                    definition.name,
                    definition.requirement,
                    definition.min_length,
                    definition.max_length,
                    value,
                    tokens,
                )
            )

    if decomposition.elements:
        emit("ISA", decomposition.elements)

    for segment in drop_null_rows(split_segments(payload)):
        elements = split_elements(segment, element_separator)
        segment_id = elements[0].decode("ascii", errors="replace")
        emit(segment_id, tuple(elements[1:]))

    return CodeInventory(occurrences, element_separator.decode("ascii", errors="replace"))
