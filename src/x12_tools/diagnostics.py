# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Adapt x12-tidy's :class:`~x12_tidy.diagnostics.Diagnostic` for display.

x12-tidy deliberately keeps severity off the ``Diagnostic`` record and resolves
it at report time from its code registry. This module does that resolution
once and flattens each finding into a plain, JSON-friendly row. Nothing here
decides *what* is wrong with an interchange -- that is entirely x12-tidy's
job; this is presentation only, for the cleanse summary shown alongside the
segment inventory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from x12_tidy.diagnostics import Diagnostic, meta, resolved_severity

#: Severities x12-tidy can assign, ordered most severe first.
SEVERITY_ORDER: tuple[str, ...] = ("fatal", "error", "warning")


@dataclass(frozen=True)
class DiagnosticView:
    """One finding, with severity resolved and a title attached."""

    severity: str
    code: str
    title: str
    message: str
    offset: int | None

    @property
    def severity_rank(self) -> int:
        try:
            return SEVERITY_ORDER.index(self.severity)
        except ValueError:  # unknown/future severity sorts last
            return len(SEVERITY_ORDER)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def view_diagnostic(diag: Diagnostic) -> DiagnosticView:
    return DiagnosticView(
        severity=resolved_severity(diag.code),
        code=diag.code.value,
        title=meta(diag.code).title,
        message=diag.message,
        offset=diag.offset,
    )


def view_diagnostics(diags: list[Diagnostic]) -> list[DiagnosticView]:
    """Resolve a list of findings, most severe first, then by byte offset."""
    views = [view_diagnostic(d) for d in diags]
    views.sort(key=lambda v: (v.severity_rank, v.offset if v.offset is not None else -1))
    return views


def severity_counts(views: list[DiagnosticView]) -> dict[str, int]:
    """Count findings per severity, always including every key in order."""
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for v in views:
        counts[v.severity] = counts.get(v.severity, 0) + 1
    return counts
