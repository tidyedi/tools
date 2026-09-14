# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""The FastAPI application: a small hub of standalone X12 EDI tools.

Routes:

* ``GET  /``              -- the tools hub (landing page, one card per tool).
* ``GET  /segments``      -- the segment-inventory tool page.
* ``POST /api/segments``  -- cleanse pasted EDI and return its segment inventory as JSON.
* ``GET  /codes``         -- the code-inventory tool page.
* ``POST /api/codes``     -- cleanse pasted EDI and return its coded-element inventory as JSON.
* ``GET  /reference``     -- what's in segment_names.py and element_definitions.py, browsable.
* ``GET  /convention``    -- the convention-PDF importer tool page.
* ``POST /api/convention``-- parse an uploaded DLA/DLMS convention PDF into a segment table and per-segment element/code detail.
* ``POST /api/export/xlsx``-- turn a table's current (filtered/sorted) rows into a real .xlsx workbook.
* ``GET  /healthz``       -- liveness probe.

Nothing submitted is stored, logged, or persisted -- each request is cleansed
and inventoried in memory and forgotten once the response is sent, the same
privacy stance as x12-tidy-web.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from x12_tools import __version__
from x12_tools.codes import build_code_inventory
from x12_tools.convention_pdf import PdftotextMissing, parse_convention_pdf
from x12_tools.element_definitions import RELEASE, SEGMENT_ELEMENTS, element_source
from x12_tools.engine import cleanse
from x12_tools.inventory import build_inventory
from x12_tools.models import MAX_EDI_CHARS, MAX_PDF_BYTES, ExportXlsxRequest, SegmentsRequest
from x12_tools.samples import SAMPLES
from x12_tools.segment_names import SEGMENT_NAMES
from x12_tools.xlsx_export import build_xlsx

_HERE = Path(__file__).parent
_TEMPLATES = Jinja2Templates(directory=str(_HERE / "templates"))

#: One entry per tool on the hub. Add a row here (and its route) as new tools
#: land -- the landing page reads this list, nothing is hardcoded twice.
TOOLS: list[dict[str, str]] = [
    {
        "slug": "segments",
        "title": "Segment inventory",
        "blurb": (
            "Paste an EDI interchange, cleanse it, and get its unique segments -- "
            "each one listed once, not once per repeat -- grouped by transaction "
            "set type. A checklist of what this EDI requires, for writing an "
            "implementation convention."
        ),
    },
    {
        "slug": "codes",
        "title": "Code inventory",
        "blurb": (
            "Paste an EDI interchange, cleanse it, and see every element's value "
            "in its actual position in the file, one row per occurrence, in true "
            "document order -- for troubleshooting: answer 'where did that value "
            "come from?' without hunting through the raw text."
        ),
    },
    {
        "slug": "convention",
        "title": "Convention importer",
        "blurb": (
            "Upload a DLA/DLMS-style implementation convention PDF and get its "
            "segment table plus every element's definition and code meanings, "
            "extracted straight from the document -- a starting point for "
            "building a convention table without retyping it by hand."
        ),
    },
    {
        "slug": "reference",
        "title": "Reference data",
        "blurb": (
            "Browse every segment and element this tool knows about, straight "
            "from segment_names.py and element_definitions.py -- searchable "
            "and sortable, so you can check coverage before pasting a file."
        ),
    },
    {
        "slug": "x12-tidy-web",
        "title": "EDI Repair",
        "url": "https://repair.tidyedi.com/",
        "blurb": (
            "A sibling tool, not part of this repo: paste a malformed X12 "
            "interchange and get back a conformant copy plus a per-pass "
            "report of every fix -- locate the ISA, recover delimiters, pad "
            "short elements, rebuild the envelope. Same privacy stance, "
            "nothing stored."
        ),
    },
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="x12-tools",
        version=__version__,
        description="A small hub of standalone online tools for working with ANSI X12 EDI.",
    )

    app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")

    @app.exception_handler(RequestValidationError)
    def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's default 422 body is deeply nested; flatten to one message
        # for the tool pages' JS to show directly.
        errors = exc.errors()
        message = errors[0]["msg"] if errors else "invalid request"
        return JSONResponse({"detail": message}, status_code=422)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request, "index.html", {"app_version": __version__, "tools": TOOLS, "current": "home"}
        )

    @app.get("/segments", response_class=HTMLResponse)
    def segments_page(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request,
            "segments.html",
            {
                "app_version": __version__,
                "max_edi_chars": MAX_EDI_CHARS,
                "samples": [
                    {"slug": s.slug, "title": s.title, "blurb": s.blurb, "edi": s.edi}
                    for s in SAMPLES
                ],
                "segment_names": SEGMENT_NAMES,
                "current": "segments",
            },
        )

    @app.get("/codes", response_class=HTMLResponse)
    def codes_page(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request,
            "codes.html",
            {
                "app_version": __version__,
                "max_edi_chars": MAX_EDI_CHARS,
                "samples": [
                    {"slug": s.slug, "title": s.title, "blurb": s.blurb, "edi": s.edi}
                    for s in SAMPLES
                ],
                "current": "codes",
            },
        )

    @app.get("/reference", response_class=HTMLResponse)
    def reference_page(request: Request) -> HTMLResponse:
        segment_ids_with_elements = set(SEGMENT_ELEMENTS)
        segment_rows = [
            {
                "segment": segment_id,
                "name": name,
                "release": RELEASE,
                "has_elements": segment_id in segment_ids_with_elements,
            }
            for segment_id, name in sorted(SEGMENT_NAMES.items())
        ]
        element_rows = [
            {
                "ref": f"{segment_id}{e.position:02d}",
                "segment": segment_id,
                "position": e.position,
                "name": e.name,
                "requirement": e.requirement,
                "data_type": e.data_type,
                "min_length": e.min_length,
                "max_length": e.max_length,
                "release": RELEASE,
                "source": element_source(segment_id),
            }
            for segment_id, elements in sorted(SEGMENT_ELEMENTS.items())
            for e in elements
        ]
        return _TEMPLATES.TemplateResponse(
            request,
            "reference.html",
            {
                "app_version": __version__,
                "segment_count": len(segment_rows),
                "element_segment_count": len(SEGMENT_ELEMENTS),
                "segment_rows": segment_rows,
                "element_rows": element_rows,
                "current": "reference",
            },
        )

    @app.get("/convention", response_class=HTMLResponse)
    def convention_page(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request,
            "convention.html",
            {"app_version": __version__, "max_pdf_bytes": MAX_PDF_BYTES, "current": "convention"},
        )

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ok", "x12_tools": __version__}

    @app.post("/api/segments")
    def api_segments(req: SegmentsRequest) -> JSONResponse:
        interchanges = []
        for result in cleanse(req.edi):
            # A fatal finding means a conforming parser would still reject
            # this interchange even though x12-tidy could locate an ISA line
            # -- withhold the segment listing rather than list segments from
            # something that isn't a valid interchange.
            inventory = (
                build_inventory(result.payload)
                if result.payload is not None and not result.has_fatal
                else None
            )
            interchanges.append(
                {
                    **result.as_dict(),
                    "inventory": inventory.as_dict() if inventory is not None else None,
                }
            )
        return JSONResponse({"interchange_count": len(interchanges), "interchanges": interchanges})

    @app.post("/api/codes")
    def api_codes(req: SegmentsRequest) -> JSONResponse:
        interchanges = []
        for result in cleanse(req.edi):
            # Same rule as /api/segments: a fatal finding means this isn't a
            # valid interchange, so there's no code inventory to report either.
            inventory = (
                build_code_inventory(result.payload)
                if result.payload is not None and not result.has_fatal
                else None
            )
            interchanges.append(
                {
                    **result.as_dict(),
                    "inventory": inventory.as_dict() if inventory is not None else None,
                }
            )
        return JSONResponse({"interchange_count": len(interchanges), "interchanges": interchanges})

    @app.post("/api/convention")
    async def api_convention(files: list[UploadFile] = File(...)) -> JSONResponse:  # noqa: B008
        # Each file is parsed independently and tagged with its own filename
        # in the response, so the page can combine several conventions into
        # one segment table / element table while still telling rows apart
        # by source file.
        results: list[dict[str, Any]] = []
        for file in files:
            filename = file.filename or "unnamed.pdf"
            if not filename.lower().endswith(".pdf"):
                return JSONResponse(
                    {"detail": f"{filename}: please upload a PDF file."}, status_code=422
                )
            data = await file.read()
            if not data:
                return JSONResponse({"detail": f"{filename}: the file is empty."}, status_code=422)
            if len(data) > MAX_PDF_BYTES:
                return JSONResponse(
                    {"detail": f"{filename}: exceeds the {MAX_PDF_BYTES:,}-byte limit."},
                    status_code=422,
                )
            try:
                parsed = parse_convention_pdf(data)
            except PdftotextMissing as exc:
                return JSONResponse({"detail": str(exc)}, status_code=503)
            except ValueError as exc:
                return JSONResponse({"detail": f"{filename}: {exc}"}, status_code=422)
            results.append({"filename": filename, **parsed.as_dict()})
        return JSONResponse({"results": results})

    @app.post("/api/export/xlsx")
    def api_export_xlsx(req: ExportXlsxRequest) -> Response:
        content = build_xlsx(req.records)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{req.filename}.xlsx"'},
        )

    return app


app = create_app()
