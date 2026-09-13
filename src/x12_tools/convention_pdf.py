# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
r"""Parse a DLA/DLMS-style X12 implementation convention PDF into structured
data: the segment table (Pos/Id/Segment Name/Req/Max Use/Repeat/Notes/Usage,
with loop context) plus, per segment, its element summary (Ref/element
number/Name/Req/Type/Min-Max/Usage) and every coded element's Code/Name
pairs -- the actual, convention-specific code meanings, straight from the
document that defines them, rather than guessed at.

Requires poppler's ``pdftotext`` on ``$PATH`` (``brew install poppler`` /
``apt-get install poppler-utils``) -- a system dependency beyond this
project's usual pip/uv packages, because no pure-Python library matched
``pdftotext -layout``'s column-preserving text extraction closely enough to
parse reliably. :func:`parse_convention_pdf` raises :class:`PdftotextMissing`
with a clear message if it isn't installed.

Approach, validated against a real DLA IC (004010F511M5MA62):

1. Extract text with ``pdftotext -layout``, which inserts a form-feed
   (``\x0c``) between pages -- letting the page structure be recovered even
   though nothing in the visible text says "new page".
2. Strip the running header/footer that repeats on every page: header lines
   are found by exact match (after whitespace normalization) across many
   pages' top few lines; the footer is found by regex (it carries a page
   number that changes per page, so it can't be matched by exact repetition)
   anchored on the one token that's the same on every footer line.
3. Parse the segment table: a numbered row (optionally starred, meaning
   "flagged" -- typically legacy/DLMS-enhancement segments), a
   ``LOOP ID - <id>`` marker (optionally starred) that sets loop context
   for the rows that follow, and a segment name that can wrap onto a
   continuation line with no leading number.
4. Parse each segment's detail page: pages are anchored on the
   ``Pos: N    Max: M`` line that precedes every one (present even for the
   very first segment), which is a far more reliable split point than trying
   to recognize segment titles directly. Within a page, element rows
   (``REF##  ElementNumber  Name  Req  Type  Min/Max  Usage``) are found by
   the ``REF##`` pattern, and a ``Code Name`` sub-header switches into
   code-row mode until the next element row or ``Description:`` line. A
   nested ``DLMS Note:`` (or numbered bullet under one) does not end code
   mode -- it's skipped in place -- since a note can sit between two code
   rows without the code list actually being over.

This is a best-effort text-layout parse of a real-world document, not a
guaranteed-correct one: a convention whose generator differs from DLA's own
will very likely need adjustments here. Rows that don't match an expected
shape are simply skipped rather than guessed at.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from typing import Any

#: Loop marker line, with an optional leading "*" (a DLMS-flagged loop).
_LOOP_RE = re.compile(r"^(?:\*\s*)?LOOP ID\s*-\s*(\S+)")
#: A numbered segment-table row: optional "*" flag, position number, the rest
#: of the row (segment ID, name, and the remaining columns).
_SEGMENT_ROW_RE = re.compile(r"^\s*(\*)?\s*(\d+)\s+(.*)$")
#: An element-summary row: a ref like "BR01", the element number, the rest.
_ELEMENT_ROW_RE = re.compile(r"^\s*([A-Z0-9]{2,3}\d{2})\s+(\d+)\s+(.*)$")
#: The "Pos: N    Max: M" line that precedes every segment detail page.
_POS_MAX_RE = re.compile(r"^\s*Pos:\s*(\S+)\s+Max:\s*(\S+)\s*$")
#: The running footer: some token (the document ID), a page number, a date.
_FOOTER_RE = re.compile(r"^(\S+)\s+\d{1,4}\s+\S.*\d{4}\s*$")
#: A code token is short and alphanumeric-ish -- distinguishes a real
#: "CODE   Name" row from a wrapped DLMS Note sentence that happens to have a
#: short first word.
_CODE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9./>\-]{0,14}$")
_BULLET_RE = re.compile(r"^\d+\.\s")


class PdftotextMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class ConventionSegmentRow:
    """One row of the segment table -- envelope or transaction-set content,
    exactly as the convention lists it (including repeats across loops)."""

    pos: str
    loop_id: str | None
    segment_id: str
    name: str
    requirement: str
    max_use: str
    repeat: str
    notes: str
    usage: str  # "Must use" / "Used" / "Not Used" -- the convention's own call
    flagged: bool  # a leading "*" -- typically a DLMS-enhancement marker

    def as_dict(self) -> dict[str, Any]:
        return {
            "pos": self.pos,
            "loop_id": self.loop_id,
            "segment_id": self.segment_id,
            "name": self.name,
            "requirement": self.requirement,
            "max_use": self.max_use,
            "repeat": self.repeat,
            "notes": self.notes,
            "usage": self.usage,
            "flagged": self.flagged,
        }


@dataclass(frozen=True)
class ConventionCode:
    code: str
    name: str

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "name": self.name}


@dataclass(frozen=True)
class ConventionElement:
    ref: str  # e.g. "BR01"
    element_number: str
    name: str
    requirement: str
    data_type: str
    min_max: str
    usage: str
    codes: list[ConventionCode]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "element_number": self.element_number,
            "name": self.name,
            "requirement": self.requirement,
            "data_type": self.data_type,
            "min_max": self.min_max,
            "usage": self.usage,
            "codes": [c.as_dict() for c in self.codes],
        }


@dataclass(frozen=True)
class ConventionSegmentDetail:
    segment_id: str
    pos: str
    max_use: str
    elements: list[ConventionElement]

    def as_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "pos": self.pos,
            "max_use": self.max_use,
            "elements": [e.as_dict() for e in self.elements],
        }


@dataclass(frozen=True)
class ParsedConvention:
    segment_table: list[ConventionSegmentRow]
    #: segment_id -> its element summary. A segment repeated across loops
    #: (e.g. LM/LQ) has one detail page describing it, not one per loop.
    segment_details: dict[str, ConventionSegmentDetail]

    def as_dict(self) -> dict[str, Any]:
        return {
            "segment_table": [r.as_dict() for r in self.segment_table],
            "segment_details": {sid: d.as_dict() for sid, d in self.segment_details.items()},
        }


def _run_pdftotext(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", "-enc", "UTF-8", tmp.name, "-"],
                capture_output=True,
                check=True,
                timeout=60,
            )
        except FileNotFoundError as exc:
            raise PdftotextMissing(
                "pdftotext (poppler) is not installed on this server -- "
                "install poppler-utils to enable PDF convention parsing."
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise ValueError(
                f"pdftotext could not read this file: {exc.stderr.decode('utf-8', errors='replace')}"
            ) from exc
    return result.stdout.decode("utf-8", errors="replace")


def _strip_running_header_footer(text: str) -> str:
    """Remove the header/footer that repeats on every page. See the module
    docstring for why header and footer need different detection strategies."""
    pages = text.split("\x0c")

    def norm(line: str) -> str:
        return re.sub(r"\s+", " ", line).strip()

    header_freq: Counter[str] = Counter()
    footer_tokens: Counter[str] = Counter()
    for page in pages:
        page_lines = page.splitlines()
        # A set, not a list: on a short page the head and tail slices can
        # overlap, and counting the same line twice from one page would let
        # page-specific content cross the boilerplate threshold on its own.
        candidates = {norm(l) for l in page_lines[:8] + page_lines[-3:] if norm(l)}
        for n in candidates:
            header_freq[n] += 1
        nonblank = [line for line in page_lines if line.strip()]
        if nonblank:
            m = _FOOTER_RE.match(nonblank[-1].strip())
            if m:
                footer_tokens[m.group(1)] += 1

    boilerplate = {n for n, count in header_freq.items() if count >= len(pages) * 0.4}
    doc_id = footer_tokens.most_common(1)[0][0] if footer_tokens else None

    cleaned_pages = []
    for page in pages:
        kept = []
        for line in page.splitlines():
            if norm(line) in boilerplate:
                continue
            if doc_id and line.strip().startswith(doc_id) and _FOOTER_RE.match(line.strip()):
                continue
            kept.append(line)
        cleaned_pages.append("\n".join(kept))
    return "\n".join(cleaned_pages)


def _parse_segment_table(lines: list[str]) -> list[ConventionSegmentRow]:
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() in ("Heading:", "Summary:"))
        end = next(i for i, l in enumerate(lines) if l.strip() == "Notes:" and i > start)
    except StopIteration:
        return []
    section = lines[start:end]

    rows: list[ConventionSegmentRow] = []
    current: ConventionSegmentRow | None = None
    current_dict: dict[str, Any] | None = None
    loop_id: str | None = None

    for raw in section:
        stripped = raw.strip()
        if not stripped or stripped in ("Heading:", "Detail:", "Summary:"):
            continue
        if stripped.startswith("Pos") and "Id" in stripped:
            continue
        loop_match = _LOOP_RE.match(stripped)
        if loop_match:
            loop_id = loop_match.group(1)
            current, current_dict = None, None
            continue
        row_match = _SEGMENT_ROW_RE.match(raw)
        if row_match:
            star, pos, rest = row_match.groups()
            cols = re.split(r"\s{2,}", rest.strip())
            if len(cols) < 4:
                continue
            repeat = cols[4] if len(cols) > 6 else ""
            notes = cols[5] if len(cols) > 6 else (cols[4] if len(cols) == 6 else "")
            current_dict = {
                "pos": pos,
                "loop_id": loop_id,
                "segment_id": cols[0],
                "name": cols[1],
                "requirement": cols[2],
                "max_use": cols[3],
                "repeat": repeat,
                "notes": notes,
                "usage": cols[-1],
                "flagged": bool(star),
            }
            rows.append(ConventionSegmentRow(**current_dict))
            current = rows[-1]
            continue
        if current is not None and current_dict is not None:
            # a wrapped segment name's continuation line
            idx = rows.index(current)
            merged = {**current_dict, "name": current_dict["name"] + " " + stripped}
            rows[idx] = ConventionSegmentRow(**merged)
            current, current_dict = rows[idx], merged

    return rows


def _parse_segment_details(lines: list[str]) -> dict[str, ConventionSegmentDetail]:
    block_starts = [i for i, l in enumerate(lines) if _POS_MAX_RE.match(l)]
    block_starts.append(len(lines))

    details: dict[str, ConventionSegmentDetail] = {}
    for idx in range(len(block_starts) - 1):
        block = lines[block_starts[idx] : block_starts[idx + 1]]
        pos_max_match = _POS_MAX_RE.match(block[0])
        assert pos_max_match is not None
        pos, max_use = pos_max_match.groups()

        segment_id = next((l.strip().split()[0] for l in block[1:] if l.strip()), None)
        if not segment_id:
            continue

        try:
            es_idx = next(i for i, l in enumerate(block) if l.strip() == "Element Summary:")
        except StopIteration:
            continue

        elements: list[ConventionElement] = []
        current: ConventionElement | None = None
        in_codes = False

        for raw in block[es_idx + 1 :]:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("Ref ") and "Element Name" in stripped:
                continue
            elem_match = _ELEMENT_ROW_RE.match(raw)
            if elem_match:
                ref, elem_num, rest = elem_match.groups()
                cols = re.split(r"\s{2,}", rest.strip())
                if len(cols) >= 4:
                    current = ConventionElement(
                        ref=ref,
                        element_number=elem_num,
                        name=cols[0],
                        requirement=cols[1],
                        data_type=cols[2],
                        min_max=cols[3],
                        usage=cols[-1],
                        codes=[],
                    )
                    elements.append(current)
                    in_codes = False
                continue
            if stripped.startswith("Description:"):
                in_codes = False
                continue
            if stripped == "Code Name":
                in_codes = True
                continue
            if stripped.startswith(("Syntax Rules:", "Semantics:", "Comments:")):
                in_codes = False
                continue
            if stripped == "DLMS Note:" or _BULLET_RE.match(stripped):
                continue  # a note between code rows -- skip it, stay in codes mode
            if in_codes and current is not None:
                cols = re.split(r"\s{2,}", stripped, maxsplit=1)
                if len(cols) == 2 and _CODE_TOKEN_RE.match(cols[0]):
                    # codes is a mutable list on an otherwise-frozen dataclass,
                    # so appending in place (rather than rebuilding the
                    # element) is safe -- `current` and `elements[-1]` are the
                    # same object.
                    current.codes.append(ConventionCode(cols[0], cols[1]))

        details[segment_id] = ConventionSegmentDetail(segment_id, pos, max_use, elements)

    return details


def parse_convention_pdf(pdf_bytes: bytes) -> ParsedConvention:
    """Parse a DLA/DLMS-style implementation convention PDF's bytes into its
    segment table and per-segment element/code detail. See the module
    docstring for the approach and its limits."""
    text = _run_pdftotext(pdf_bytes)
    cleaned = _strip_running_header_footer(text)
    lines = cleaned.splitlines()
    return ParsedConvention(
        segment_table=_parse_segment_table(lines),
        segment_details=_parse_segment_details(lines),
    )
