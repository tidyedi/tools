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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from x12_tools import __version__
from x12_tools.codes import build_code_inventory
from x12_tools.convention_pdf import PdftotextMissing, parse_convention_pdf
from x12_tools.element_definitions import SEGMENT_ELEMENTS
from x12_tools.engine import cleanse
from x12_tools.inventory import build_inventory
from x12_tools.models import MAX_EDI_CHARS, MAX_PDF_BYTES, SegmentsRequest
from x12_tools.samples import SAMPLES
from x12_tools.segment_names import SEGMENT_NAMES

_HERE = Path(__file__).parent
_TEMPLATES = Jinja2Templates(directory=str(_HERE / "templates"))

#: One entry per tool on the hub. Add a row here (and its route) as new tools
#: land -- the landing page reads this list, nothing is hardcoded twice.
TOOLS: list[dict[str, str]] = [
    {
        "slug": "segments",
        "title": "Segment inventory",
        "blurb": (
            "Paste an EDI interchange, cleanse it, and get the unique segments it "
            "contains, grouped by transaction set type -- a starting point for "
            "writing an implementation convention."
        ),
    },
    {
        "slug": "codes",
        "title": "Code inventory",
        "blurb": (
            "Paste an EDI interchange, cleanse it, and get every distinct value "
            "seen in each coded element (N101, REF01, and similar) -- a starting "
            "point for spotting codes your convention doesn't cover yet."
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
        return _TEMPLATES.TemplateResponse(
            request,
            "reference.html",
            {
                "app_version": __version__,
                "segment_names": SEGMENT_NAMES,
                "segment_elements": {
                    segment_id: [
                        {
                            "position": e.position,
                            "name": e.name,
                            "requirement": e.requirement,
                            "data_type": e.data_type,
                            "min_length": e.min_length,
                            "max_length": e.max_length,
                        }
                        for e in elements
                    ]
                    for segment_id, elements in sorted(SEGMENT_ELEMENTS.items())
                },
                # Segments with a name but no full element breakdown yet --
                # shown separately so the gap between the two references is
                # visible rather than silently implied.
                "name_only_segments": sorted(set(SEGMENT_NAMES) - segment_ids_with_elements),
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
    async def api_convention(file: UploadFile = File(...)) -> JSONResponse:  # noqa: B008 (FastAPI idiom)
        if not (file.filename or "").lower().endswith(".pdf"):
            return JSONResponse({"detail": "Please upload a PDF file."}, status_code=422)
        data = await file.read()
        if not data:
            return JSONResponse({"detail": "The uploaded file is empty."}, status_code=422)
        if len(data) > MAX_PDF_BYTES:
            return JSONResponse(
                {"detail": f"File exceeds the {MAX_PDF_BYTES:,}-byte limit."}, status_code=422
            )
        try:
            result = parse_convention_pdf(data)
        except PdftotextMissing as exc:
            return JSONResponse({"detail": str(exc)}, status_code=503)
        except ValueError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=422)
        return JSONResponse(result.as_dict())

    return app


app = create_app()
