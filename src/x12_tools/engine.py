# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Cleanse pasted EDI text with x12-tidy, one result per interchange found.

:func:`x12_tidy.tidy` already reconstructs each interchange it can locate into
a clean, conformant payload in a single call -- the multi-pass loop in
x12-tidy-web exists to make its *report* legible pass by pass, not because one
call leaves the payload half-repaired. This module wants the repaired bytes,
not a pass-by-pass narrative, so it calls ``tidy`` once and adapts what comes
back for display and for :mod:`x12_tools.inventory` to walk.

A submission can hold more than one interchange (a flat-file batch); ``tidy``
already splits on that, so this module returns one :class:`CleanResult` per
interchange, in order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from x12_tidy import EnvelopeFacts, tidy

from x12_tools.diagnostics import DiagnosticView, severity_counts, view_diagnostics

#: The byte<->text codec. Latin-1 is a total, round-tripping map between bytes
#: 0-255 and the first 256 code points, so any byte sequence survives a
#: ``.decode("latin-1").encode("latin-1")`` round trip unchanged.
TEXT_CODEC = "latin-1"


def _s(value: bytes) -> str:
    return value.decode(TEXT_CODEC, errors="replace").strip()


def _iso_date(raw: str) -> str:
    """ISA09 is always 6-digit ``YYMMDD`` (the ISA segment's shape doesn't
    change across releases -- only GS04 grew to 8-digit CCYYMMDD). Rendered as
    ``YYYY-MM-DD``, assuming 20xx -- the only reasonable reading for EDI
    traffic today. Anything else that shows up here (already-repaired by
    x12-tidy, so this should be rare) is returned unchanged rather than
    guessed at."""
    if len(raw) == 6 and raw.isdigit():
        return f"20{raw[0:2]}-{raw[2:4]}-{raw[4:6]}"
    return raw


@dataclass(frozen=True)
class EnvelopeFactsView:
    """The envelope facts a companion guide needs beyond the segment list
    itself -- who it's from/to and what release it's written at. Pulled
    straight from x12-tidy's own :class:`~x12_tidy.EnvelopeFacts`, which
    ``tidy()`` already computes; this just decodes and trims it for display."""

    sender_qualifier: str
    sender_id: str
    receiver_qualifier: str
    receiver_id: str
    interchange_date: str
    interchange_time: str
    interchange_version: str  # ISA12, e.g. "00401"
    usage_indicator: str  # "P" / "T" / "I"
    group_versions: list[str]  # GS08 per functional group, e.g. ["004010"]

    @classmethod
    def from_facts(cls, facts: EnvelopeFacts) -> EnvelopeFactsView:
        return cls(
            sender_qualifier=_s(facts.sender_qualifier),
            sender_id=_s(facts.sender_id),
            receiver_qualifier=_s(facts.receiver_qualifier),
            receiver_id=_s(facts.receiver_id),
            interchange_date=_iso_date(_s(facts.interchange_date)),
            interchange_time=_s(facts.interchange_time),
            interchange_version=_s(facts.interchange_version),
            usage_indicator=_s(facts.usage_indicator),
            group_versions=[_s(v) for v in facts.group_versions],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "sender_qualifier": self.sender_qualifier,
            "sender_id": self.sender_id,
            "receiver_qualifier": self.receiver_qualifier,
            "receiver_id": self.receiver_id,
            "interchange_date": self.interchange_date,
            "interchange_time": self.interchange_time,
            "interchange_version": self.interchange_version,
            "usage_indicator": self.usage_indicator,
            "group_versions": self.group_versions,
        }


@dataclass(frozen=True)
class CleanResult:
    """One interchange's cleanse outcome."""

    index: int  # 1-based, in submission order
    recovered: bool  # False iff no ISA line could be located at all
    was_clean: bool  # True iff x12-tidy found nothing to flag
    cleansed_text: str | None  # None iff not recovered
    payload: bytes | None  # the same bytes, for inventory.py to walk
    diagnostics: list[DiagnosticView]
    facts: EnvelopeFactsView | None  # None iff not recovered

    @property
    def severity_counts(self) -> dict[str, int]:
        return severity_counts(self.diagnostics)

    @property
    def has_fatal(self) -> bool:
        """True when a fatal finding remains after cleansing -- an ISA line
        was located (``recovered``), but a conforming parser would still
        reject the interchange (e.g. a functional-group-count mismatch). The
        segment inventory isn't meaningful over a payload like that, so
        callers should withhold it rather than list segments from something
        that isn't actually a valid interchange."""
        return self.severity_counts["fatal"] > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "recovered": self.recovered,
            "has_fatal": self.has_fatal,
            "was_clean": self.was_clean,
            "cleansed_text": self.cleansed_text,
            "severity_counts": self.severity_counts,
            "diagnostics": [d.as_dict() for d in self.diagnostics],
            "facts": self.facts.as_dict() if self.facts is not None else None,
        }


def cleanse(source: str | bytes) -> list[CleanResult]:
    """Run x12-tidy over ``source``, returning one :class:`CleanResult` per
    interchange it finds (always at least one -- see ``x12_tidy.tidy``)."""
    data = source.encode(TEXT_CODEC, errors="replace") if isinstance(source, str) else bytes(source)

    results = []
    for i, result in enumerate(tidy(data), start=1):
        results.append(
            CleanResult(
                index=i,
                recovered=result.payload is not None,
                was_clean=bool(result.was_clean),
                cleansed_text=(
                    None if result.payload is None else result.payload.decode(TEXT_CODEC, errors="replace")
                ),
                payload=result.payload,
                diagnostics=view_diagnostics(list(result.diagnostics)),
                facts=EnvelopeFactsView.from_facts(result.facts) if result.facts is not None else None,
            )
        )
    return results
