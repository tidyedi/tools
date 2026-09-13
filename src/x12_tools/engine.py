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

from x12_tidy import tidy

from x12_tools.diagnostics import DiagnosticView, severity_counts, view_diagnostics

#: The byte<->text codec. Latin-1 is a total, round-tripping map between bytes
#: 0-255 and the first 256 code points, so any byte sequence survives a
#: ``.decode("latin-1").encode("latin-1")`` round trip unchanged.
TEXT_CODEC = "latin-1"


@dataclass(frozen=True)
class CleanResult:
    """One interchange's cleanse outcome."""

    index: int  # 1-based, in submission order
    recovered: bool  # False iff no ISA line could be located at all
    was_clean: bool  # True iff x12-tidy found nothing to flag
    cleansed_text: str | None  # None iff not recovered
    payload: bytes | None  # the same bytes, for inventory.py to walk
    diagnostics: list[DiagnosticView]

    @property
    def severity_counts(self) -> dict[str, int]:
        return severity_counts(self.diagnostics)

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "recovered": self.recovered,
            "was_clean": self.was_clean,
            "cleansed_text": self.cleansed_text,
            "severity_counts": self.severity_counts,
            "diagnostics": [d.as_dict() for d in self.diagnostics],
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
            )
        )
    return results
