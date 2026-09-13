# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""``x12-tools`` -- run the web app.

    x12-tools serve [--host H] [--port P] [--reload]
"""

from __future__ import annotations

import argparse
import os

from x12_tools import __version__


def _default_port() -> int:
    """Serve port: ``$PORT`` if the host sets one (Cloud Run, Render, Fly,
    Railway all do), otherwise 8000."""
    raw = os.environ.get("PORT")
    if raw and raw.isdigit():
        return int(raw)
    return 8000


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="x12-tools", description=__doc__)
    parser.add_argument("--version", action="version", version=f"x12-tools {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the web application")
    serve.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    serve.add_argument(
        "--port",
        type=int,
        default=_default_port(),
        help="bind port (default: $PORT if set, else 8000)",
    )
    serve.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev)")
    serve.add_argument("--log-level", default="info", help="uvicorn log level (default: info)")
    return parser


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "x12_tools.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "serve":
        return _cmd_serve(args)
    return 2  # pragma: no cover  (argparse enforces `required=True`)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
