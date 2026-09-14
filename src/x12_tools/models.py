# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Pydantic schemas for the JSON API. Kept thin -- these only validate and
clamp user input; the response shape is each endpoint's own plain dict."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

#: Reject anything larger than this up front (characters of submitted EDI
#: text). One interchange is rarely over ~100 KB; this is generous and bounds
#: abuse, matching x12-tidy-web's own limit.
MAX_EDI_CHARS = 2_000_000

#: Reject a convention PDF upload larger than this (bytes). A DLA IC PDF is
#: rarely over a few MB even with dozens of segment detail pages; generous
#: headroom, bounds abuse rather than typical use.
MAX_PDF_BYTES = 25_000_000

#: Reject an Excel export with more rows than this. The page already
#: rendered these rows in the browser, so this is only an abuse bound, not
#: a realistic ceiling.
MAX_EXPORT_ROWS = 50_000


class SegmentsRequest(BaseModel):
    edi: str = Field(..., description="The X12 EDI text to cleanse and inventory.")

    @field_validator("edi")
    @classmethod
    def _not_empty_not_huge(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("no EDI text was provided")
        if len(value) > MAX_EDI_CHARS:
            raise ValueError(f"input exceeds the {MAX_EDI_CHARS:,}-character limit")
        return value


class ExportXlsxRequest(BaseModel):
    """One table's current (filtered/sorted) rows, exactly as the page is
    showing them -- turned into a real .xlsx workbook server-side so the
    pages never need to load a client-side spreadsheet library."""

    filename: str = Field(..., description="Base filename, without extension.")
    #: Row order here is preserved in the workbook -- whatever order the
    #: page's own sort/filter state produced.
    records: list[dict[str, Any]] = Field(..., description="One dict per row, column label -> value.")

    @field_validator("filename")
    @classmethod
    def _safe_filename(cls, value: str) -> str:
        value = value.strip() or "export"
        # Strip anything that isn't safe in a Content-Disposition filename or
        # across filesystems -- this never touches disk, but the browser
        # writes it to one.
        return "".join(c for c in value if c.isalnum() or c in "-_") or "export"

    @field_validator("records")
    @classmethod
    def _not_too_many(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(value) > MAX_EXPORT_ROWS:
            raise ValueError(f"export exceeds the {MAX_EXPORT_ROWS:,}-row limit")
        return value
