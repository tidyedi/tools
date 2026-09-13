# x12-tools

A small hub of standalone online tools for working with ANSI X12 EDI. Same
shape as [x12-tidy-web](https://github.com/tidyedi/x12-tidy-web): a FastAPI
front end, no account, nothing you paste is stored, logged, or sent anywhere.

## Tools

- **Segment inventory** (`/segments`) — paste an EDI interchange, cleanse it
  with [x12-tidy](https://github.com/tidyedi/x12-tidy), and get the unique
  segments it contains, grouped by transaction set type (ST01, e.g. `850`).
  Occurrences of the same transaction set type are merged into one list, in
  first-appearance order — a starting point for writing an implementation
  convention / companion guide.

## Run it locally

```bash
uv sync
uv run x12-tools serve     # http://127.0.0.1:8000
```

Options: `x12-tools serve --host 0.0.0.0 --port 8080 --reload`. The server
honours `$PORT` when set.

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
