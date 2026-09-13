# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""The FastAPI application: a small hub of standalone X12 EDI tools.

Routes:

* ``GET  /``              -- the tools hub (landing page, one card per tool).
* ``GET  /segments``      -- the segment-inventory tool page.
* ``POST /api/segments``  -- cleanse pasted EDI and return its segment inventory as JSON.
* ``GET  /healthz``       -- liveness probe.

Nothing submitted is stored, logged, or persisted -- each request is cleansed
and inventoried in memory and forgotten once the response is sent, the same
privacy stance as x12-tidy-web.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from x12_tools import __version__
from x12_tools.engine import cleanse
from x12_tools.inventory import build_inventory
from x12_tools.models import MAX_EDI_CHARS, SegmentsRequest
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

    return app


app = create_app()
