# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz

from __future__ import annotations

from x12_tools.engine import cleanse


def test_cleanse_conformant_input_is_clean(two_orders_edi: str) -> None:
    results = cleanse(two_orders_edi)
    assert len(results) == 1
    result = results[0]
    assert result.recovered
    assert result.was_clean
    assert result.diagnostics == []
    assert result.payload is not None


def test_cleanse_unrecoverable_input() -> None:
    results = cleanse("not an EDI file at all")
    assert len(results) == 1
    assert results[0].recovered is False
    assert results[0].payload is None
    assert results[0].cleansed_text is None
