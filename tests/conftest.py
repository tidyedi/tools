# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Shared EDI fixtures for the test suite."""

from __future__ import annotations

import pytest

#: A conformant interchange with two occurrences of the same transaction set
#: type (850), each using a different subset of segments -- exercises merging
#: unique segments across occurrences of the same type.
TWO_ORDERS_EDI = (
    "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
    "240101*1200*U*00401*000000001*0*P*:~"
    "GS*PO*SENDERGS*RECEIVERID*20240101*1200*1*X*004010~"
    "ST*850*0001~BEG*00*NE*PO0001**20240101~N1*ST*Warehouse~SE*4*0001~"
    "ST*850*0002~BEG*00*NE*PO0002**20240101~PO1*1*24*CA*18.50**BP*ITEM~SE*4*0002~"
    "GE*2*1~IEA*1*000000001~"
)


@pytest.fixture()
def two_orders_edi() -> str:
    return TWO_ORDERS_EDI
