# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Per-element definitions -- name, requirement, data type, and length --
for the elements of the segments this package already knows about (see
:mod:`x12_tools.segment_names`).

Like the segment name, an element's *definition* is part of the ANSI X12
element dictionary: fixed by the standard, independent of release or which
transaction set the segment shows up in. ``requirement`` here is the
element's own designator *within this segment* (Mandatory / Optional /
Conditional) -- not to be confused with the segment-level Requirement column
in the convention table, which is a decision about the segment as a whole.

Data types follow X12's own vocabulary:

* ``ID``  -- a coded value from a controlled list (what
  :func:`x12_tools.codes.build_code_inventory` scans for).
* ``AN``  -- string (alphanumeric).
* ``DT``  -- date, ``CCYYMMDD`` (8) or the older ``YYMMDD`` (6, ISA09 only).
* ``TM``  -- time, ``HHMM`` up to ``HHMMSSdd``.
* ``N0``  -- integer.
* ``R``   -- decimal (implied or explicit).

ISA's widths are fixed-format (min == max for every position) and are taken
directly from x12-tidy's own :data:`~x12_tidy.envelope.isa.reconstruct.ISA_ELEMENT_WIDTHS`
-- the table it uses to repair a short ISA element -- rather than re-derived
here, so the two never drift apart.

Deliberately not exhaustive: a segment or position missing here just hasn't
been added yet, the same "blank means not covered" contract as
:mod:`x12_tools.segment_names`. Composite elements (e.g. ``QTY03``, ``HI``'s
whole shape) are left out rather than flattened incorrectly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from x12_tidy.envelope.isa.reconstruct import ISA_ELEMENT_WIDTHS

DataType = Literal["ID", "AN", "DT", "TM", "N0", "R"]
Requirement = Literal["M", "O", "C"]


@dataclass(frozen=True)
class ElementDefinition:
    position: int  # 1-based, matching X12's own element numbering
    name: str
    requirement: Requirement
    data_type: DataType
    min_length: int
    max_length: int


def _isa_definitions() -> list[ElementDefinition]:
    names = (
        "Authorization Information Qualifier",
        "Authorization Information",
        "Security Information Qualifier",
        "Security Information",
        "Interchange ID Qualifier",
        "Interchange Sender ID",
        "Interchange ID Qualifier",
        "Interchange Receiver ID",
        "Interchange Date",
        "Interchange Time",
        "Repetition Separator / Interchange Control Standards Identifier",
        "Interchange Control Version Number",
        "Interchange Control Number",
        "Acknowledgment Requested",
        "Usage Indicator",
        "Component Element Separator",
    )
    types: tuple[DataType, ...] = (
        "ID", "AN", "ID", "AN", "ID", "AN", "ID", "AN",
        "DT", "TM", "ID", "ID", "N0", "ID", "ID", "AN",
    )
    return [
        # ISA is fixed-format -- min == max == the width x12-tidy repairs to.
        ElementDefinition(i, name, "M", dtype, width, width)
        for i, (name, dtype, width) in enumerate(zip(names, types, ISA_ELEMENT_WIDTHS), start=1)
    ]


#: segment_id -> its elements, in position order.
SEGMENT_ELEMENTS: dict[str, list[ElementDefinition]] = {
    "ISA": _isa_definitions(),
    "GS": [
        ElementDefinition(1, "Functional Identifier Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Application Sender's Code", "M", "AN", 2, 15),
        ElementDefinition(3, "Application Receiver's Code", "M", "AN", 2, 15),
        ElementDefinition(4, "Date", "M", "DT", 8, 8),
        ElementDefinition(5, "Time", "M", "TM", 4, 8),
        ElementDefinition(6, "Group Control Number", "M", "N0", 1, 9),
        ElementDefinition(7, "Responsible Agency Code", "M", "ID", 1, 2),
        ElementDefinition(8, "Version / Release / Industry Identifier Code", "M", "AN", 1, 12),
    ],
    "ST": [
        ElementDefinition(1, "Transaction Set Identifier Code", "M", "ID", 3, 3),
        ElementDefinition(2, "Transaction Set Control Number", "M", "AN", 4, 9),
        ElementDefinition(3, "Implementation Convention Reference", "O", "AN", 1, 35),
    ],
    "SE": [
        ElementDefinition(1, "Number of Included Segments", "M", "N0", 1, 10),
        ElementDefinition(2, "Transaction Set Control Number", "M", "AN", 4, 9),
    ],
    "GE": [
        ElementDefinition(1, "Number of Transaction Sets Included", "M", "N0", 1, 6),
        ElementDefinition(2, "Group Control Number", "M", "N0", 1, 9),
    ],
    "IEA": [
        ElementDefinition(1, "Number of Included Functional Groups", "M", "N0", 1, 5),
        ElementDefinition(2, "Interchange Control Number", "M", "N0", 9, 9),
    ],
    "BEG": [
        ElementDefinition(1, "Transaction Set Purpose Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Purchase Order Type Code", "M", "ID", 2, 2),
        ElementDefinition(3, "Purchase Order Number", "M", "AN", 1, 22),
        ElementDefinition(4, "Release Number", "O", "AN", 1, 30),
        ElementDefinition(5, "Date", "M", "DT", 8, 8),
        ElementDefinition(6, "Contract Number", "O", "AN", 1, 30),
    ],
    "BAK": [
        ElementDefinition(1, "Transaction Set Purpose Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Acknowledgment Type", "M", "ID", 2, 2),
        ElementDefinition(3, "Purchase Order Number", "M", "AN", 1, 22),
        ElementDefinition(4, "Date", "O", "DT", 8, 8),
    ],
    "BSN": [
        ElementDefinition(1, "Transaction Set Purpose Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Shipment Identification", "M", "AN", 2, 30),
        ElementDefinition(3, "Date", "M", "DT", 8, 8),
        ElementDefinition(4, "Time", "M", "TM", 4, 8),
    ],
    "BPR": [
        ElementDefinition(1, "Transaction Handling Code", "M", "ID", 1, 2),
        ElementDefinition(2, "Monetary Amount", "M", "R", 1, 18),
        ElementDefinition(3, "Credit/Debit Flag Code", "M", "ID", 1, 1),
        ElementDefinition(4, "Payment Method Code", "M", "ID", 3, 3),
    ],
    "TRN": [
        ElementDefinition(1, "Trace Type Code", "M", "ID", 1, 2),
        ElementDefinition(2, "Reference Identification", "M", "AN", 1, 50),
    ],
    "N1": [
        ElementDefinition(1, "Entity Identifier Code", "M", "ID", 2, 3),
        ElementDefinition(2, "Name", "O", "AN", 1, 60),
        ElementDefinition(3, "Identification Code Qualifier", "O", "ID", 1, 2),
        ElementDefinition(4, "Identification Code", "O", "AN", 2, 80),
    ],
    "N3": [
        ElementDefinition(1, "Address Information", "M", "AN", 1, 55),
        ElementDefinition(2, "Address Information", "O", "AN", 1, 55),
    ],
    "N4": [
        ElementDefinition(1, "City Name", "O", "AN", 2, 30),
        ElementDefinition(2, "State or Province Code", "O", "ID", 2, 2),
        ElementDefinition(3, "Postal Code", "O", "ID", 3, 15),
        ElementDefinition(4, "Country Code", "O", "ID", 2, 3),
    ],
    "N9": [
        ElementDefinition(1, "Reference Identification Qualifier", "M", "ID", 2, 3),
        ElementDefinition(2, "Reference Identification", "O", "AN", 1, 30),
    ],
    "NM1": [
        ElementDefinition(1, "Entity Identifier Code", "M", "ID", 2, 3),
        ElementDefinition(2, "Entity Type Qualifier", "M", "ID", 1, 1),
        ElementDefinition(3, "Name Last or Organization Name", "O", "AN", 1, 60),
        ElementDefinition(4, "Name First", "O", "AN", 1, 35),
        ElementDefinition(5, "Name Middle", "O", "AN", 1, 25),
        ElementDefinition(6, "Name Prefix", "O", "AN", 1, 10),
        ElementDefinition(7, "Name Suffix", "O", "AN", 1, 10),
        ElementDefinition(8, "Identification Code Qualifier", "O", "ID", 1, 2),
        ElementDefinition(9, "Identification Code", "O", "AN", 2, 80),
    ],
    "PER": [
        ElementDefinition(1, "Contact Function Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Name", "O", "AN", 1, 60),
        ElementDefinition(3, "Communication Number Qualifier", "O", "ID", 2, 2),
        ElementDefinition(4, "Communication Number", "O", "AN", 1, 80),
        ElementDefinition(5, "Communication Number Qualifier", "O", "ID", 2, 2),
        ElementDefinition(6, "Communication Number", "O", "AN", 1, 80),
        ElementDefinition(7, "Communication Number Qualifier", "O", "ID", 2, 2),
        ElementDefinition(8, "Communication Number", "O", "AN", 1, 80),
    ],
    "REF": [
        ElementDefinition(1, "Reference Identification Qualifier", "M", "ID", 2, 3),
        ElementDefinition(2, "Reference Identification", "O", "AN", 1, 30),
        ElementDefinition(3, "Description", "O", "AN", 1, 80),
    ],
    "DTM": [
        ElementDefinition(1, "Date/Time Qualifier", "M", "ID", 3, 3),
        ElementDefinition(2, "Date", "O", "DT", 8, 8),
        ElementDefinition(3, "Time", "O", "TM", 4, 8),
    ],
    "DTP": [
        ElementDefinition(1, "Date/Time Qualifier", "M", "ID", 3, 3),
        ElementDefinition(2, "Date Time Period Format Qualifier", "M", "ID", 2, 3),
        ElementDefinition(3, "Date Time Period", "M", "AN", 1, 35),
    ],
    "PO1": [
        ElementDefinition(1, "Assigned Identification", "O", "AN", 1, 20),
        ElementDefinition(2, "Quantity Ordered", "O", "R", 1, 15),
        ElementDefinition(3, "Unit or Basis for Measurement Code", "O", "ID", 2, 2),
        ElementDefinition(4, "Unit Price", "O", "R", 1, 17),
        ElementDefinition(5, "Basis of Unit Price Code", "O", "ID", 2, 2),
        ElementDefinition(6, "Product/Service ID Qualifier", "O", "ID", 2, 2),
        ElementDefinition(7, "Product/Service ID", "O", "AN", 1, 48),
        ElementDefinition(8, "Product/Service ID Qualifier", "O", "ID", 2, 2),
        ElementDefinition(9, "Product/Service ID", "O", "AN", 1, 48),
    ],
    "PID": [
        ElementDefinition(1, "Item Description Type", "M", "ID", 1, 1),
        ElementDefinition(2, "Product/Process Characteristic Code", "O", "ID", 2, 3),
        ElementDefinition(3, "Agency Qualifier Code", "O", "ID", 1, 2),
        ElementDefinition(4, "Product Description Code", "O", "AN", 1, 12),
        ElementDefinition(5, "Description", "O", "AN", 1, 80),
    ],
    "TD1": [
        ElementDefinition(1, "Packaging Code", "O", "ID", 3, 5),
        ElementDefinition(2, "Lading Quantity", "O", "N0", 1, 7),
    ],
    "TD3": [
        ElementDefinition(1, "Transportation Method/Type Code", "O", "ID", 1, 2),
    ],
    "TD4": [
        ElementDefinition(1, "Special Handling Code", "O", "ID", 1, 3),
    ],
    "TD5": [
        ElementDefinition(1, "Routing Sequence Code", "O", "ID", 1, 2),
        ElementDefinition(2, "Identification Code Qualifier", "O", "ID", 1, 2),
        ElementDefinition(3, "Identification Code", "O", "AN", 1, 25),
        ElementDefinition(4, "Transportation Method/Type Code", "O", "ID", 1, 2),
        ElementDefinition(5, "Routing", "O", "AN", 1, 35),
    ],
    "FOB": [
        ElementDefinition(1, "Shipment Method of Payment", "M", "ID", 2, 2),
        ElementDefinition(2, "Location Qualifier", "O", "ID", 1, 2),
        ElementDefinition(3, "Description", "O", "AN", 1, 80),
        ElementDefinition(4, "Transportation Terms Qualifier Code", "O", "ID", 2, 2),
        ElementDefinition(5, "Transportation Terms Code", "O", "ID", 3, 3),
    ],
    "ITD": [
        ElementDefinition(1, "Terms Type Code", "O", "ID", 2, 2),
        ElementDefinition(2, "Terms Basis Date Code", "O", "ID", 1, 2),
        ElementDefinition(3, "Terms Discount Percent", "O", "R", 1, 6),
        ElementDefinition(4, "Terms Discount Due Date", "O", "DT", 8, 8),
        ElementDefinition(5, "Terms Discount Days Due", "O", "N0", 1, 3),
        ElementDefinition(6, "Terms Net Due Date", "O", "DT", 8, 8),
        ElementDefinition(7, "Terms Net Days", "O", "N0", 1, 3),
    ],
    "TXI": [
        ElementDefinition(1, "Tax Type Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Monetary Amount", "O", "R", 1, 18),
    ],
    "AMT": [
        ElementDefinition(1, "Amount Qualifier Code", "M", "ID", 1, 3),
        ElementDefinition(2, "Monetary Amount", "M", "R", 1, 18),
    ],
    "QTY": [
        ElementDefinition(1, "Quantity Qualifier", "M", "ID", 2, 2),
        ElementDefinition(2, "Quantity", "M", "R", 1, 15),
    ],
    "MEA": [
        ElementDefinition(1, "Measurement Reference ID Code", "O", "ID", 2, 2),
        ElementDefinition(2, "Measurement Qualifier", "O", "ID", 1, 3),
        ElementDefinition(3, "Measurement Value", "O", "R", 1, 20),
    ],
    "CTP": [
        ElementDefinition(1, "Class of Trade Code", "O", "ID", 2, 2),
        ElementDefinition(2, "Price Identifier Code", "O", "ID", 3, 3),
        ElementDefinition(3, "Unit Price", "O", "R", 1, 17),
    ],
    "SAC": [
        ElementDefinition(1, "Allowance or Charge Indicator", "M", "ID", 1, 1),
        ElementDefinition(2, "Service, Promotion, Allowance, or Charge Code", "O", "ID", 4, 4),
        ElementDefinition(3, "Agency Qualifier Code", "O", "ID", 2, 2),
    ],
    "CTT": [
        ElementDefinition(1, "Number of Line Items", "M", "N0", 1, 6),
        ElementDefinition(2, "Hash Total", "O", "R", 1, 10),
    ],
    "HL": [
        ElementDefinition(1, "Hierarchical ID Number", "M", "AN", 1, 12),
        ElementDefinition(2, "Hierarchical Parent ID Number", "O", "AN", 1, 12),
        ElementDefinition(3, "Hierarchical Level Code", "M", "ID", 1, 2),
        ElementDefinition(4, "Hierarchical Child Code", "O", "ID", 1, 1),
    ],
    "SBR": [
        ElementDefinition(1, "Payer Responsibility Sequence Number Code", "M", "ID", 1, 1),
        ElementDefinition(2, "Individual Relationship Code", "O", "ID", 2, 2),
    ],
    "CAS": [
        ElementDefinition(1, "Claim Adjustment Group Code", "M", "ID", 1, 2),
    ],
    "INS": [
        ElementDefinition(1, "Yes/No Condition or Response Code", "M", "ID", 1, 1),
        ElementDefinition(2, "Individual Relationship Code", "M", "ID", 2, 2),
    ],
    "DMG": [
        ElementDefinition(1, "Date Time Period Format Qualifier", "O", "ID", 2, 3),
        ElementDefinition(2, "Date Time Period", "O", "AN", 1, 35),
        ElementDefinition(3, "Gender Code", "O", "ID", 1, 1),
    ],
}
