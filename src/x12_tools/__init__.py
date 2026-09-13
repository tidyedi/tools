# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""x12-tools: a small hub of standalone online tools for working with ANSI X12 EDI.

The first tool, segment inventory, pastes and cleanses an EDI interchange (via
:mod:`x12_tidy`) and lists the unique segments it contains, grouped by
transaction set type -- a starting point for writing an implementation
convention / companion guide.
"""

from __future__ import annotations

__version__ = "0.1.0"
