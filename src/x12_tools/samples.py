# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Sample interchanges the segment-inventory form can load, so a visitor has
something to test with before they have their own EDI to paste.

Each one is picked to show a different facet of the inventory:

* ``single-850`` -- one transaction set, one occurrence. The baseline case.
* ``batch-850`` -- the same transaction set type three times in one functional
  group, each occurrence using a slightly different subset of segments --
  shows the merge-across-occurrences behaviour and the occurrence count.
* ``mixed-850-855`` -- two different transaction set types in one functional
  group -- shows each type getting its own group.
* ``needs-cleanse`` -- an email-forwarded 850 with junk before the ISA, short
  ISA elements, and a functional-group count that overstates what's actually
  there. x12-tidy repairs what it can and still hands back a payload, so the
  inventory runs even though one finding remains unresolved -- shows that the
  cleanse step is doing real work, not a no-op, before the segments are listed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    slug: str
    title: str
    blurb: str  # one sentence, shown under the sample picker
    edi: str


SAMPLES: tuple[Sample, ...] = (
    Sample(
        slug="single-850",
        title="850 purchase order — one transaction set",
        blurb="A single, conformant purchase order: one ST/SE loop, nothing to merge.",
        edi=(
            "ISA*00*          *00*          *ZZ*NORTHWIND      *ZZ*CONTOSO        *"
            "240401*0915*U*00401*000000501*0*P*:~"
            "GS*PO*NORTHWIND*CONTOSO*20240401*0915*501*X*004010~"
            "ST*850*0001~"
            "BEG*00*NE*PO-2024-0501**20240401~"
            "N1*ST*Northwind Traders Warehouse 3~"
            "PO1*1*24*CA*18.50**BP*NW-COFFEE-005~"
            "PO1*2*6*EA*42.00**BP*NW-GRINDER-XL~"
            "CTT*2~"
            "SE*7*0001~"
            "GE*1*501~"
            "IEA*1*000000501~"
        ),
    ),
    Sample(
        slug="batch-850",
        title="850 batch — three purchase orders, same release",
        blurb=(
            "The same transaction set type (850) three times in one functional "
            "group, each using a different subset of segments — shows how "
            "occurrences of a type merge into one segment list."
        ),
        edi=(
            "ISA*00*          *00*          *ZZ*NORTHWIND      *ZZ*CONTOSO        *"
            "240402*0900*U*00401*000000502*0*P*:~"
            "GS*PO*NORTHWIND*CONTOSO*20240402*0900*502*X*004010~"
            "ST*850*0001~BEG*00*NE*PO-1**20240402~N1*ST*Warehouse A~"
            "PO1*1*10*EA*5.00**BP*ITEM-A~SE*5*0001~"
            "ST*850*0002~BEG*00*NE*PO-2**20240402~"
            "PO1*1*20*EA*7.50**BP*ITEM-B~REF*IA*INTERNAL-2~SE*5*0002~"
            "ST*850*0003~BEG*00*NE*PO-3**20240402~N1*ST*Warehouse C~"
            "PO1*1*5*EA*12.00**BP*ITEM-C~CTT*1~SE*6*0003~"
            "GE*3*502~"
            "IEA*1*000000502~"
        ),
    ),
    Sample(
        slug="mixed-850-855",
        title="850 + 855 in one batch — two transaction set types",
        blurb="An order and its acknowledgment in the same functional group — each type gets its own group.",
        edi=(
            "ISA*00*          *00*          *ZZ*NORTHWIND      *ZZ*CONTOSO        *"
            "240403*1000*U*00401*000000503*0*P*:~"
            "GS*PO*NORTHWIND*CONTOSO*20240403*1000*503*X*004010~"
            "ST*850*0001~BEG*00*NE*PO-9**20240403~PO1*1*3*EA*9.99**BP*WIDGET~SE*4*0001~"
            "ST*855*0002~BAK*00*AC*PO-9**20240403~PO1*1*3*EA*9.99**BP*WIDGET~SE*4*0002~"
            "GE*2*503~"
            "IEA*1*000000503~"
        ),
    ),
    Sample(
        slug="needs-cleanse",
        title="Forwarded email — cannot be fully repaired",
        blurb=(
            "An email header sits before the ISA and four ISA elements were "
            "trimmed below their fixed width; x12-tidy repairs those but IEA01 "
            "still overstates the functional-group count -- a fatal finding "
            "x12-tidy won't guess a fix for, so the segment list is withheld."
        ),
        edi=(
            "Subject: FW: Q1 reorder - please confirm\r\n"
            "From: purchasing@northwind-traders.example\r\n\r\n"
            "ISA*00*   *00*   *ZZ*NORTHWIND*ZZ*CONTOSO*240401*0915*U*00401*000000501*0*P*:~"
            "GS*PO*NORTHWIND*CONTOSO*20240401*0915*501*X*004010~"
            "ST*850*0001~"
            "BEG*00*NE*PO-2024-0501**20240401~"
            "N1*ST*Northwind Traders Warehouse 3~"
            "PO1*1*24*CA*18.50**BP*NW-COFFEE-005~"
            "PO1*2*6*EA*42.00**BP*NW-GRINDER-XL~"
            "CTT*2~"
            "SE*7*0001~"
            "GE*1*501~"
            "IEA*2*000000501~"
        ),
    ),
)
