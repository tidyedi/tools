# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Pydantic schemas for the JSON API. Kept thin -- these only validate and
clamp user input; the response shape is each endpoint's own plain dict."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

#: Reject anything larger than this up front (characters of submitted EDI
#: text). One interchange is rarely over ~100 KB; this is generous and bounds
#: abuse, matching x12-tidy-web's own limit.
MAX_EDI_CHARS = 2_000_000


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
