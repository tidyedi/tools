# x12-tools

A small hub of standalone online tools for working with ANSI X12 EDI. Same
shape as [x12-tidy-web](https://github.com/tidyedi/x12-tidy-web): a FastAPI
front end, no account, nothing you paste is stored, logged, or sent anywhere.

## Tools

- **Segment inventory** (`/segments`) — paste an EDI interchange, cleanse it
  with [x12-tidy](https://github.com/tidyedi/x12-tidy), and get an editable
  convention table: the unique segments it contains (envelope folded in),
  element/populated counts, and a Segment name/Requirement/Notes you fill in
  — grouped by transaction set type, occurrences merged into one list.
- **Code inventory** (`/codes`) — same cleanse, but lists every distinct
  value seen in each coded (ID-type) element (N101, REF01, and similar),
  alongside that element's definition from `element_definitions.py`.
- **Convention importer** (`/convention`) — upload a DLA/DLMS-style
  implementation convention PDF and get its segment table plus every
  element's definition and code meanings, parsed straight out of the
  document (see `convention_pdf.py`). Requires poppler's `pdftotext` — see
  below.
- **Reference data** (`/reference`) — browse what `segment_names.py` and
  `element_definitions.py` actually cover.

## Run it locally

```bash
uv sync
uv run x12-tools serve     # http://127.0.0.1:8000
```

Options: `x12-tools serve --host 0.0.0.0 --port 8080 --reload`. The server
honours `$PORT` when set.

### System dependency: poppler

The Convention importer shells out to poppler's `pdftotext` (no pure-Python
library matched its `-layout` column-preserving text extraction closely
enough to parse reliably). Install it separately from the Python
dependencies:

```bash
brew install poppler          # macOS
apt-get install poppler-utils # Debian/Ubuntu
```

Every other tool works without it; `/api/convention` returns a clear 503 if
`pdftotext` isn't on `$PATH`.

## Develop

```bash
uv run pytest
uv run ruff check .
uv run mypy src tests
```

## Adding a new tool

1. Add the tool's logic in its own module under `src/x12_tools/` (see
   `inventory.py` for the segment-inventory tool's shape: pure functions over
   x12-tidy's output, no framework code).
2. Add a route and a template in `src/x12_tools/app.py` /
   `src/x12_tools/templates/`.
3. Add an entry to the `TOOLS` list in `app.py` so it shows up on the hub
   (`/`).
