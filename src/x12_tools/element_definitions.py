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
* ``N2``  -- decimal with an implied 2 decimal places (e.g. ``12345`` -> 123.45).
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

DataType = Literal["ID", "AN", "DT", "TM", "N0", "N2", "R"]
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
    # Sourced from Stedi's public X12 segment reference (stedi.com/edi/x12/segment/<CODE>).
    # Positions that are composite elements are left out, same rule as above (e.g. ACK 7-26,
    # CLM 5 & 11, HI's whole shape) -- gaps in the position sequence below are expected.
    "ACK": [
        ElementDefinition(1, "Line Item Status Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Quantity", "C", "R", 1, 15),
        ElementDefinition(3, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(4, "Date/Time Qualifier", "O", "ID", 3, 3),
        ElementDefinition(5, "Date", "C", "DT", 8, 8),
        ElementDefinition(6, "Request Reference Number", "O", "AN", 1, 45),
        ElementDefinition(27, "Agency Qualifier Code", "C", "ID", 2, 2),
        ElementDefinition(28, "Source Subqualifier", "C", "AN", 1, 15),
        ElementDefinition(29, "Industry Code", "C", "AN", 1, 30),
    ],
    "AK1": [
        ElementDefinition(1, "Functional Identifier Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Group Control Number", "M", "N0", 1, 9),
        ElementDefinition(3, "Version / Release / Industry Identifier Code", "O", "AN", 1, 12),
    ],
    "AK2": [
        ElementDefinition(1, "Transaction Set Identifier Code", "M", "ID", 3, 3),
        ElementDefinition(2, "Transaction Set Control Number", "M", "AN", 4, 9),
        ElementDefinition(3, "Implementation Convention Reference", "O", "AN", 1, 35),
    ],
    "AK3": [
        ElementDefinition(1, "Segment ID Code", "M", "ID", 2, 3),
        ElementDefinition(2, "Segment Position in Transaction Set", "M", "N0", 1, 10),
        ElementDefinition(3, "Loop Identifier Code", "O", "AN", 1, 6),
        ElementDefinition(4, "Segment Syntax Error Code", "O", "ID", 1, 3),
    ],
    "AK4": [
        # AK4-01 (C030, Position in Segment) is a composite -- left out.
        ElementDefinition(2, "Data Element Reference Code", "O", "AN", 1, 4),
        ElementDefinition(3, "Data Element Syntax Error Code", "M", "ID", 1, 3),
        ElementDefinition(4, "Copy of Bad Data Element", "O", "AN", 1, 99),
    ],
    "AK5": [
        ElementDefinition(1, "Transaction Set Acknowledgment Code", "M", "ID", 1, 1),
        ElementDefinition(2, "Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(3, "Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(4, "Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(5, "Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(6, "Transaction Set Syntax Error Code", "O", "ID", 1, 3),
    ],
    "AK9": [
        ElementDefinition(1, "Functional Group Acknowledge Code", "M", "ID", 1, 1),
        ElementDefinition(2, "Number of Transaction Sets Included", "M", "N0", 1, 6),
        ElementDefinition(3, "Number of Received Transaction Sets", "M", "N0", 1, 6),
        ElementDefinition(4, "Number of Accepted Transaction Sets", "M", "N0", 1, 6),
        ElementDefinition(5, "Functional Group Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(6, "Functional Group Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(7, "Functional Group Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(8, "Functional Group Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(9, "Functional Group Syntax Error Code", "O", "ID", 1, 3),
    ],
    "B10": [
        ElementDefinition(1, "Reference Identification", "C", "AN", 1, 80),
        ElementDefinition(2, "Shipment Identification Number", "O", "AN", 1, 30),
        ElementDefinition(3, "Standard Carrier Alpha Code", "M", "ID", 2, 4),
        ElementDefinition(4, "Inquiry Request Number", "O", "N0", 1, 3),
        ElementDefinition(5, "Reference Identification Qualifier", "C", "ID", 2, 3),
        ElementDefinition(6, "Reference Identification", "C", "AN", 1, 80),
        ElementDefinition(7, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(8, "Date", "C", "DT", 8, 8),
        ElementDefinition(9, "Time", "C", "TM", 4, 8),
    ],
    "B2": [
        ElementDefinition(1, "Tariff Service Code", "O", "ID", 2, 2),
        ElementDefinition(2, "Standard Carrier Alpha Code", "O", "ID", 2, 4),
        ElementDefinition(3, "Standard Point Location Code", "O", "ID", 6, 9),
        ElementDefinition(4, "Shipment Identification Number", "O", "AN", 1, 30),
        ElementDefinition(5, "Weight Unit Code", "O", "ID", 1, 1),
        ElementDefinition(6, "Shipment Method of Payment Code", "M", "ID", 2, 2),
        ElementDefinition(7, "Shipment Qualifier", "O", "ID", 1, 1),
        ElementDefinition(8, "Total Equipment", "O", "N0", 1, 3),
        ElementDefinition(9, "Shipment Weight Code", "O", "ID", 1, 1),
        ElementDefinition(10, "Customs Documentation Handling Code", "O", "ID", 2, 2),
        ElementDefinition(11, "Transportation Terms Code", "O", "ID", 3, 3),
        ElementDefinition(12, "Payment Method Code", "O", "ID", 3, 3),
    ],
    "B2A": [
        ElementDefinition(1, "Transaction Set Purpose Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Application Type Code", "O", "ID", 2, 2),
    ],
    "BCH": [
        ElementDefinition(1, "Transaction Set Purpose Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Purchase Order Type Code", "M", "ID", 2, 2),
        ElementDefinition(3, "Purchase Order Number", "M", "AN", 1, 22),
        ElementDefinition(4, "Release Number", "O", "AN", 1, 30),
        ElementDefinition(5, "Change Order Sequence Number", "O", "AN", 1, 8),
        ElementDefinition(6, "Date", "M", "DT", 8, 8),
        ElementDefinition(7, "Request Reference Number", "O", "AN", 1, 45),
        ElementDefinition(8, "Contract Number", "O", "AN", 1, 30),
        ElementDefinition(9, "Reference Identification", "O", "AN", 1, 80),
        ElementDefinition(10, "Date", "O", "DT", 8, 8),
        ElementDefinition(11, "Date", "O", "DT", 8, 8),
        ElementDefinition(12, "Contract Type Code", "O", "ID", 2, 2),
        ElementDefinition(13, "Security Level Code", "O", "ID", 2, 2),
        ElementDefinition(14, "Acknowledgment Type Code", "O", "ID", 2, 2),
        ElementDefinition(15, "Transaction Type Code", "O", "ID", 2, 2),
        ElementDefinition(16, "Purchase Category Code", "O", "ID", 2, 2),
    ],
    "BGN": [
        ElementDefinition(1, "Transaction Set Purpose Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Reference Identification", "M", "AN", 1, 80),
        ElementDefinition(3, "Date", "M", "DT", 8, 8),
        ElementDefinition(4, "Time", "C", "TM", 4, 8),
        ElementDefinition(5, "Time Code", "O", "ID", 2, 2),
        ElementDefinition(6, "Reference Identification", "O", "AN", 1, 80),
        ElementDefinition(7, "Transaction Type Code", "O", "ID", 2, 2),
        ElementDefinition(8, "Action Code", "O", "ID", 1, 2),
        ElementDefinition(9, "Security Level Code", "O", "ID", 2, 2),
    ],
    "BIG": [
        ElementDefinition(1, "Date", "M", "DT", 8, 8),
        ElementDefinition(2, "Invoice Number", "M", "AN", 1, 22),
        ElementDefinition(3, "Date", "O", "DT", 8, 8),
        ElementDefinition(4, "Purchase Order Number", "O", "AN", 1, 22),
        ElementDefinition(5, "Release Number", "O", "AN", 1, 30),
        ElementDefinition(6, "Change Order Sequence Number", "O", "AN", 1, 8),
        ElementDefinition(7, "Transaction Type Code", "O", "ID", 2, 2),
        ElementDefinition(8, "Transaction Set Purpose Code", "O", "ID", 2, 2),
        ElementDefinition(9, "Action Code", "O", "ID", 1, 2),
        ElementDefinition(10, "Invoice Number", "O", "AN", 1, 22),
        ElementDefinition(11, "Hierarchical Structure Code", "O", "ID", 4, 4),
    ],
    "CAD": [
        ElementDefinition(1, "Transportation Method/Type Code", "M", "ID", 1, 2),
        ElementDefinition(2, "Equipment Initial", "O", "AN", 1, 4),
        ElementDefinition(3, "Equipment Number", "O", "AN", 1, 15),
        ElementDefinition(4, "Standard Carrier Alpha Code", "C", "ID", 2, 4),
        ElementDefinition(5, "Routing", "C", "AN", 1, 35),
        ElementDefinition(6, "Shipment/Order Status Code", "O", "ID", 2, 2),
        ElementDefinition(7, "Reference Identification Qualifier", "O", "ID", 2, 3),
        ElementDefinition(8, "Reference Identification", "C", "AN", 1, 80),
        ElementDefinition(9, "Service Level Code", "O", "ID", 2, 2),
    ],
    "CLM": [
        # CLM05 (C023) and CLM11 (C024) are composites -- left out.
        ElementDefinition(1, "Claim Submitter's Identifier", "M", "AN", 1, 38),
        ElementDefinition(2, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(3, "Claim Filing Indicator Code", "O", "ID", 1, 2),
        ElementDefinition(4, "Non-Institutional Claim Type Code", "O", "ID", 1, 2),
        ElementDefinition(6, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(7, "Provider Accept Assignment Code", "O", "ID", 1, 1),
        ElementDefinition(8, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(9, "Release of Information Code", "O", "ID", 1, 1),
        ElementDefinition(10, "Patient Signature Source Code", "O", "ID", 1, 1),
        ElementDefinition(12, "Special Program Code", "O", "ID", 2, 3),
        ElementDefinition(13, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(14, "Level of Service Code", "O", "ID", 1, 3),
        ElementDefinition(15, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(16, "Provider Agreement Code", "O", "ID", 1, 1),
        ElementDefinition(17, "Claim Status Code", "O", "ID", 1, 2),
        ElementDefinition(18, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(19, "Claim Submission Reason Code", "O", "ID", 2, 2),
        ElementDefinition(20, "Delay Reason Code", "O", "ID", 1, 2),
        ElementDefinition(21, "Claim Authorization Exception Code", "O", "ID", 1, 2),
    ],
    "CLP": [
        # CLP11 (C022, Health Care Code Information) is a composite -- left out.
        ElementDefinition(1, "Claim Submitter's Identifier", "M", "AN", 1, 38),
        ElementDefinition(2, "Claim Status Code", "M", "ID", 1, 2),
        ElementDefinition(3, "Monetary Amount", "M", "R", 1, 18),
        ElementDefinition(4, "Monetary Amount", "M", "R", 1, 18),
        ElementDefinition(5, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(6, "Claim Filing Indicator Code", "O", "ID", 1, 2),
        ElementDefinition(7, "Reference Identification", "O", "AN", 1, 80),
        ElementDefinition(8, "Facility Code Value", "O", "AN", 1, 3),
        ElementDefinition(9, "Claim Frequency Type Code", "O", "ID", 1, 1),
        ElementDefinition(10, "Patient Discharge Status", "O", "ID", 1, 2),
        ElementDefinition(12, "Quantity", "C", "R", 1, 15),
        ElementDefinition(13, "Percentage as Decimal", "O", "R", 1, 10),
        ElementDefinition(14, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(15, "Exchange Rate", "O", "R", 4, 10),
        ElementDefinition(16, "Source of Payment Typology Code", "O", "ID", 2, 6),
    ],
    "COB": [
        ElementDefinition(1, "Payer Responsibility Sequence Number Code", "O", "ID", 1, 1),
        ElementDefinition(2, "Reference Identification", "O", "AN", 1, 80),
        ElementDefinition(3, "Coordination of Benefits Code", "O", "ID", 1, 1),
        ElementDefinition(4, "Service Type Code", "O", "ID", 1, 2),
    ],
    "CSH": [
        ElementDefinition(1, "Sales Requirement Code", "O", "ID", 1, 2),
        ElementDefinition(2, "Action Code", "O", "ID", 1, 2),
        ElementDefinition(3, "Amount", "C", "N2", 1, 15),
        ElementDefinition(4, "Account Number", "O", "AN", 1, 35),
        ElementDefinition(5, "Date", "O", "DT", 8, 8),
        ElementDefinition(6, "Agency Qualifier Code", "C", "ID", 2, 2),
        ElementDefinition(7, "Special Services Code", "C", "ID", 2, 10),
        ElementDefinition(8, "Product/Service Substitution Code", "O", "ID", 1, 2),
        ElementDefinition(9, "Percentage as Decimal", "C", "R", 1, 10),
        ElementDefinition(10, "Percent Qualifier", "C", "ID", 1, 2),
    ],
    "CTX": [
        # CTX01 (C998), CTX05 (C030), and CTX06 (C999) are composites -- left out.
        ElementDefinition(2, "Segment ID Code", "O", "ID", 2, 3),
        ElementDefinition(3, "Segment Position in Transaction Set", "O", "N0", 1, 10),
        ElementDefinition(4, "Loop Identifier Code", "O", "AN", 1, 6),
    ],
    "CUR": [
        ElementDefinition(1, "Entity Identifier Code", "M", "ID", 2, 3),
        ElementDefinition(2, "Currency Code", "M", "ID", 3, 3),
        ElementDefinition(3, "Exchange Rate", "O", "R", 4, 10),
        ElementDefinition(4, "Entity Identifier Code", "O", "ID", 2, 3),
        ElementDefinition(5, "Currency Code", "O", "ID", 3, 3),
        ElementDefinition(6, "Currency Market/Exchange Code", "O", "ID", 3, 3),
        ElementDefinition(7, "Date/Time Qualifier", "C", "ID", 3, 3),
        ElementDefinition(8, "Date", "O", "DT", 8, 8),
        ElementDefinition(9, "Time", "O", "TM", 4, 8),
        ElementDefinition(10, "Date/Time Qualifier", "C", "ID", 3, 3),
        ElementDefinition(11, "Date", "C", "DT", 8, 8),
        ElementDefinition(12, "Time", "C", "TM", 4, 8),
        ElementDefinition(13, "Date/Time Qualifier", "C", "ID", 3, 3),
        ElementDefinition(14, "Date", "C", "DT", 8, 8),
        ElementDefinition(15, "Time", "C", "TM", 4, 8),
        ElementDefinition(16, "Date/Time Qualifier", "C", "ID", 3, 3),
        ElementDefinition(17, "Date", "C", "DT", 8, 8),
        ElementDefinition(18, "Time", "C", "TM", 4, 8),
        ElementDefinition(19, "Date/Time Qualifier", "C", "ID", 3, 3),
        ElementDefinition(20, "Date", "C", "DT", 8, 8),
        ElementDefinition(21, "Time", "C", "TM", 4, 8),
    ],
    "ENT": [
        ElementDefinition(1, "Assigned Number", "O", "N0", 1, 9),
        ElementDefinition(2, "Entity Identifier Code", "C", "ID", 2, 3),
        ElementDefinition(3, "Identification Code Qualifier", "C", "ID", 1, 2),
        ElementDefinition(4, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(5, "Entity Identifier Code", "C", "ID", 2, 3),
        ElementDefinition(6, "Identification Code Qualifier", "C", "ID", 1, 2),
        ElementDefinition(7, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(8, "Reference Identification Qualifier", "C", "ID", 2, 3),
        ElementDefinition(9, "Reference Identification", "C", "AN", 1, 80),
    ],
    "G61": [
        ElementDefinition(1, "Contact Function Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Name", "M", "AN", 1, 60),
        ElementDefinition(3, "Communication Number Qualifier", "C", "ID", 2, 2),
        ElementDefinition(4, "Communication Number", "C", "AN", 1, 2048),
        ElementDefinition(5, "Contact Inquiry Reference", "O", "AN", 1, 20),
    ],
    "G62": [
        ElementDefinition(1, "Date Qualifier", "C", "ID", 2, 2),
        ElementDefinition(2, "Date", "C", "DT", 8, 8),
        ElementDefinition(3, "Time Qualifier", "C", "ID", 1, 2),
        ElementDefinition(4, "Time", "C", "TM", 4, 8),
        ElementDefinition(5, "Time Code", "O", "ID", 2, 2),
    ],
    "G72": [
        ElementDefinition(1, "Allowance or Charge Code", "M", "ID", 1, 3),
        ElementDefinition(2, "Allowance or Charge Method of Handling Code", "M", "ID", 2, 2),
        ElementDefinition(3, "Allowance or Charge Number", "C", "AN", 1, 16),
        ElementDefinition(4, "Exception Number", "O", "AN", 1, 16),
        ElementDefinition(5, "Allowance or Charge Rate", "C", "R", 1, 15),
        ElementDefinition(6, "Allowance or Charge Quantity", "C", "R", 1, 10),
        ElementDefinition(7, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(8, "Allowance or Charge Total Amount", "C", "N2", 1, 15),
        ElementDefinition(9, "Percent, Decimal Format", "C", "R", 1, 6),
        ElementDefinition(10, "Dollar Basis For Percent", "C", "R", 1, 9),
        ElementDefinition(11, "Option Number", "O", "AN", 1, 20),
        ElementDefinition(12, "Description", "O", "AN", 1, 80),
    ],
    "HD": [
        ElementDefinition(1, "Maintenance Type Code", "M", "ID", 3, 3),
        ElementDefinition(2, "Maintenance Reason Code", "O", "ID", 2, 3),
        ElementDefinition(3, "Insurance Line Code", "O", "ID", 2, 3),
        ElementDefinition(4, "Plan Coverage Description", "O", "AN", 1, 50),
        ElementDefinition(5, "Coverage Level Code", "O", "ID", 3, 3),
        ElementDefinition(6, "Count", "O", "N0", 1, 9),
        ElementDefinition(7, "Count", "O", "N0", 1, 9),
        ElementDefinition(8, "Underwriting Decision Code", "O", "ID", 1, 1),
        ElementDefinition(9, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(10, "Drug House Code", "O", "ID", 2, 3),
        ElementDefinition(11, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
    ],
    # HI's whole shape is composite (every position is C022) -- left out entirely,
    # same as the module docstring's example.
    "IK3": [
        ElementDefinition(1, "Segment ID Code", "M", "ID", 2, 3),
        ElementDefinition(2, "Segment Position in Transaction Set", "M", "N0", 1, 10),
        ElementDefinition(3, "Loop Identifier Code", "O", "AN", 1, 6),
        ElementDefinition(4, "Implementation Segment Syntax Error Code", "O", "ID", 1, 3),
    ],
    "IK4": [
        # IK4-01 (C030, Position in Segment) is a composite -- left out.
        ElementDefinition(2, "Data Element Reference Code", "O", "AN", 1, 4),
        ElementDefinition(3, "Implementation Data Element Syntax Error Code", "M", "ID", 1, 3),
        ElementDefinition(4, "Copy of Bad Data Element", "O", "AN", 1, 99),
    ],
    "IK5": [
        ElementDefinition(1, "Transaction Set Acknowledgment Code", "M", "ID", 1, 1),
        ElementDefinition(2, "Implementation Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(3, "Implementation Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(4, "Implementation Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(5, "Implementation Transaction Set Syntax Error Code", "O", "ID", 1, 3),
        ElementDefinition(6, "Implementation Transaction Set Syntax Error Code", "O", "ID", 1, 3),
    ],
    "IT1": [
        # Stops at IT1-09 -- IT1-10 through IT1-25 are further qualifier/ID
        # repeats, same call as PO1 above.
        ElementDefinition(1, "Assigned Identification", "O", "AN", 1, 20),
        ElementDefinition(2, "Quantity Invoiced", "C", "R", 1, 15),
        ElementDefinition(3, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(4, "Unit Price", "C", "R", 1, 17),
        ElementDefinition(5, "Basis of Unit Price Code", "O", "ID", 2, 2),
        ElementDefinition(6, "Product/Service ID Qualifier", "C", "ID", 2, 2),
        ElementDefinition(7, "Product/Service ID", "C", "AN", 1, 80),
        ElementDefinition(8, "Product/Service ID Qualifier", "C", "ID", 2, 2),
        ElementDefinition(9, "Product/Service ID", "C", "AN", 1, 80),
    ],
    "IT3": [
        ElementDefinition(1, "Number of Units Shipped", "C", "R", 1, 10),
        ElementDefinition(2, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(3, "Shipment/Order Status Code", "C", "ID", 2, 2),
        ElementDefinition(4, "Quantity Difference", "C", "R", 1, 9),
        ElementDefinition(5, "Change Reason Code", "C", "ID", 2, 2),
    ],
    "ITA": [
        ElementDefinition(1, "Allowance or Charge Indicator Code", "M", "ID", 1, 1),
        ElementDefinition(2, "Agency Qualifier Code", "C", "ID", 2, 2),
        ElementDefinition(3, "Special Services Code", "C", "ID", 2, 10),
        ElementDefinition(4, "Allowance or Charge Method of Handling Code", "M", "ID", 2, 2),
        ElementDefinition(5, "Allowance or Charge Number", "O", "AN", 1, 16),
        ElementDefinition(6, "Allowance or Charge Rate", "O", "R", 1, 15),
        ElementDefinition(7, "Allowance or Charge Total Amount", "O", "N2", 1, 15),
        ElementDefinition(8, "Allowance/Charge Percent Qualifier", "O", "ID", 1, 1),
        ElementDefinition(9, "Percent, Decimal Format", "C", "R", 1, 6),
        ElementDefinition(10, "Quantity", "C", "R", 1, 15),
        ElementDefinition(11, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(12, "Quantity", "C", "R", 1, 15),
        ElementDefinition(13, "Description", "C", "AN", 1, 80),
        ElementDefinition(14, "Special Charge or Allowance Code", "C", "ID", 3, 3),
        ElementDefinition(15, "Source Subqualifier", "O", "AN", 1, 15),
        ElementDefinition(16, "Relationship Code", "O", "ID", 1, 1),
        ElementDefinition(17, "Unit or Basis for Measurement Code", "O", "ID", 2, 2),
    ],
    "K3": [
        # K3-03 (C001, Composite Unit of Measure) is a composite -- left out.
        ElementDefinition(1, "Fixed Format Information", "M", "AN", 1, 80),
        ElementDefinition(2, "Record Format Code", "O", "ID", 1, 2),
    ],
    "L11": [
        ElementDefinition(1, "Reference Identification", "C", "AN", 1, 80),
        ElementDefinition(2, "Reference Identification Qualifier", "C", "ID", 2, 3),
        ElementDefinition(3, "Description", "C", "AN", 1, 80),
        ElementDefinition(4, "Date", "O", "DT", 8, 8),
        ElementDefinition(5, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
    ],
    "L3": [
        ElementDefinition(1, "Weight", "C", "R", 1, 10),
        ElementDefinition(2, "Weight Qualifier", "C", "ID", 1, 2),
        ElementDefinition(3, "Freight Rate", "C", "R", 1, 15),
        ElementDefinition(4, "Rate/Value Qualifier", "C", "ID", 2, 2),
        ElementDefinition(5, "Amount Charged", "O", "N2", 1, 15),
        ElementDefinition(6, "Advances", "O", "N2", 1, 9),
        ElementDefinition(7, "Prepaid Amount", "O", "N2", 1, 15),
        ElementDefinition(8, "Special Charge or Allowance Code", "O", "ID", 3, 3),
        ElementDefinition(9, "Volume", "C", "R", 1, 8),
        ElementDefinition(10, "Volume Unit Qualifier", "C", "ID", 1, 1),
        ElementDefinition(11, "Lading Quantity", "O", "N0", 1, 7),
        ElementDefinition(12, "Weight Unit Code", "O", "ID", 1, 1),
        ElementDefinition(13, "Tariff Number", "O", "AN", 1, 7),
        ElementDefinition(14, "Declared Value", "C", "N2", 2, 12),
        ElementDefinition(15, "Rate/Value Qualifier", "C", "ID", 2, 2),
    ],
    "LIN": [
        # Stops at LIN-10 -- up to LIN-31 repeats the same qualifier/ID pair.
        ElementDefinition(1, "Assigned Identification", "O", "AN", 1, 20),
        ElementDefinition(2, "Product/Service ID Qualifier", "M", "ID", 2, 2),
        ElementDefinition(3, "Product/Service ID", "M", "AN", 1, 80),
        ElementDefinition(4, "Product/Service ID Qualifier", "C", "ID", 2, 2),
        ElementDefinition(5, "Product/Service ID", "C", "AN", 1, 80),
        ElementDefinition(6, "Product/Service ID Qualifier", "C", "ID", 2, 2),
        ElementDefinition(7, "Product/Service ID", "C", "AN", 1, 80),
        ElementDefinition(8, "Product/Service ID Qualifier", "C", "ID", 2, 2),
        ElementDefinition(9, "Product/Service ID", "C", "AN", 1, 80),
        ElementDefinition(10, "Product/Service ID Qualifier", "C", "ID", 2, 2),
    ],
    "LUI": [
        ElementDefinition(1, "Identification Code Qualifier", "C", "ID", 1, 2),
        ElementDefinition(2, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(3, "Description", "C", "AN", 1, 80),
        ElementDefinition(4, "Use of Language Indicator Code", "O", "ID", 1, 2),
        ElementDefinition(5, "Language Proficiency Indicator Code", "O", "ID", 1, 1),
    ],
    "LX": [
        ElementDefinition(1, "Assigned Number", "M", "N0", 1, 9),
    ],
    "MAN": [
        ElementDefinition(1, "Marks and Numbers Qualifier", "M", "ID", 1, 2),
        ElementDefinition(2, "Marks and Numbers", "M", "AN", 1, 48),
        ElementDefinition(3, "Marks and Numbers", "O", "AN", 1, 48),
        ElementDefinition(4, "Marks and Numbers Qualifier", "C", "ID", 1, 2),
        ElementDefinition(5, "Marks and Numbers", "C", "AN", 1, 48),
        ElementDefinition(6, "Marks and Numbers", "O", "AN", 1, 48),
    ],
    "MSG": [
        ElementDefinition(1, "Free-form Message Text", "M", "AN", 1, 264),
        ElementDefinition(2, "Printer Carriage Control Code", "C", "ID", 2, 2),
        ElementDefinition(3, "Number", "O", "N0", 1, 9),
    ],
    "N2": [
        ElementDefinition(1, "Name", "M", "AN", 1, 60),
        ElementDefinition(2, "Name", "O", "AN", 1, 60),
    ],
    "NTE": [
        ElementDefinition(1, "Note Reference Code", "O", "ID", 3, 3),
        ElementDefinition(2, "Description", "M", "AN", 1, 80),
    ],
    "PLB": [
        # PLB03/05/07/09/11/13 (C042, Adjustment Identifier) are composites -- left out.
        ElementDefinition(1, "Reference Identification", "M", "AN", 1, 80),
        ElementDefinition(2, "Date", "M", "DT", 8, 8),
        ElementDefinition(4, "Monetary Amount", "M", "R", 1, 18),
        ElementDefinition(6, "Monetary Amount", "C", "R", 1, 18),
        ElementDefinition(8, "Monetary Amount", "C", "R", 1, 18),
        ElementDefinition(10, "Monetary Amount", "C", "R", 1, 18),
        ElementDefinition(12, "Monetary Amount", "C", "R", 1, 18),
        ElementDefinition(14, "Monetary Amount", "C", "R", 1, 18),
    ],
    "PO4": [
        ElementDefinition(1, "Pack", "O", "N0", 1, 6),
        ElementDefinition(2, "Size", "C", "R", 1, 8),
        ElementDefinition(3, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(4, "Packaging Code", "C", "AN", 3, 5),
        ElementDefinition(5, "Weight Qualifier", "O", "ID", 1, 2),
        ElementDefinition(6, "Gross Weight per Pack", "C", "R", 1, 9),
        ElementDefinition(7, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(8, "Gross Volume per Pack", "C", "R", 1, 9),
        ElementDefinition(9, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(10, "Length", "C", "R", 1, 8),
        ElementDefinition(11, "Width", "C", "R", 1, 8),
        ElementDefinition(12, "Height", "C", "R", 1, 8),
        ElementDefinition(13, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(14, "Inner Pack", "O", "N0", 1, 6),
        ElementDefinition(15, "Surface/Layer/Position Code", "O", "ID", 2, 2),
        ElementDefinition(16, "Assigned Identification", "C", "AN", 1, 20),
        ElementDefinition(17, "Assigned Identification", "O", "AN", 1, 20),
        ElementDefinition(18, "Number", "O", "N0", 1, 9),
    ],
    "POC": [
        # POC04 (Change Quantities) and POC05 (Composite Unit of Measure) are
        # composites -- left out. Stops at POC-07 -- POC-08 through POC-27
        # repeats the same qualifier/ID pair.
        ElementDefinition(1, "Assigned Identification", "O", "AN", 1, 20),
        ElementDefinition(2, "Change or Response Type Code", "M", "ID", 2, 2),
        ElementDefinition(3, "Quantity", "O", "R", 1, 15),
        ElementDefinition(6, "Unit Price", "C", "R", 1, 17),
        ElementDefinition(7, "Basis of Unit Price Code", "O", "ID", 2, 2),
    ],
    "PRF": [
        ElementDefinition(1, "Purchase Order Number", "M", "AN", 1, 22),
        ElementDefinition(2, "Release Number", "O", "AN", 1, 30),
        ElementDefinition(3, "Change Order Sequence Number", "O", "AN", 1, 8),
        ElementDefinition(4, "Date", "O", "DT", 8, 8),
        ElementDefinition(5, "Assigned Identification", "O", "AN", 1, 20),
        ElementDefinition(6, "Contract Number", "O", "AN", 1, 30),
        ElementDefinition(7, "Purchase Order Type Code", "O", "ID", 2, 2),
    ],
    "PRV": [
        # PRV05 (Provider Specialty Information) is a composite -- left out.
        ElementDefinition(1, "Provider Code", "M", "ID", 1, 3),
        ElementDefinition(2, "Reference Identification Qualifier", "C", "ID", 2, 3),
        ElementDefinition(3, "Reference Identification", "C", "AN", 1, 80),
        ElementDefinition(4, "State or Province Code", "O", "ID", 2, 2),
        ElementDefinition(6, "Provider Organization Code", "O", "ID", 3, 3),
    ],
    "PWK": [
        # PWK08 (C002, Actions Indicated) is a composite -- left out.
        ElementDefinition(1, "Report Type Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Report Transmission Code", "O", "ID", 1, 2),
        ElementDefinition(3, "Report Copies Needed", "O", "N0", 1, 2),
        ElementDefinition(4, "Entity Identifier Code", "O", "ID", 2, 3),
        ElementDefinition(5, "Identification Code Qualifier", "C", "ID", 1, 2),
        ElementDefinition(6, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(7, "Description", "O", "AN", 1, 80),
        ElementDefinition(9, "Request Category Code", "O", "ID", 1, 2),
        ElementDefinition(10, "Code List Qualifier Code", "C", "ID", 1, 3),
        ElementDefinition(11, "Industry Code", "C", "AN", 1, 30),
    ],
    "RMR": [
        ElementDefinition(1, "Reference Identification Qualifier", "C", "ID", 2, 3),
        ElementDefinition(2, "Reference Identification", "C", "AN", 1, 80),
        ElementDefinition(3, "Payment Action Code", "O", "ID", 2, 2),
        ElementDefinition(4, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(5, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(6, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(7, "Adjustment Reason Code", "C", "ID", 2, 2),
        ElementDefinition(8, "Monetary Amount", "C", "R", 1, 18),
    ],
    "S5": [
        ElementDefinition(1, "Stop Sequence Number", "M", "N0", 1, 3),
        ElementDefinition(2, "Stop Reason Code", "M", "ID", 2, 2),
        ElementDefinition(3, "Weight", "C", "R", 1, 10),
        ElementDefinition(4, "Weight Unit Code", "C", "ID", 1, 1),
        ElementDefinition(5, "Number of Units Shipped", "C", "R", 1, 10),
        ElementDefinition(6, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(7, "Volume", "C", "R", 1, 8),
        ElementDefinition(8, "Volume Unit Qualifier", "C", "ID", 1, 1),
        ElementDefinition(9, "Description", "O", "AN", 1, 80),
        ElementDefinition(10, "Standard Point Location Code", "O", "ID", 6, 9),
        ElementDefinition(11, "Accomplish Code", "O", "ID", 1, 1),
    ],
    "SCH": [
        ElementDefinition(1, "Quantity", "M", "R", 1, 15),
        ElementDefinition(2, "Unit or Basis for Measurement Code", "M", "ID", 2, 2),
        ElementDefinition(3, "Entity Identifier Code", "O", "ID", 2, 3),
        ElementDefinition(4, "Name", "C", "AN", 1, 60),
        ElementDefinition(5, "Date/Time Qualifier", "M", "ID", 3, 3),
        ElementDefinition(6, "Date", "M", "DT", 8, 8),
        ElementDefinition(7, "Time", "O", "TM", 4, 8),
        ElementDefinition(8, "Date/Time Qualifier", "C", "ID", 3, 3),
        ElementDefinition(9, "Date", "C", "DT", 8, 8),
        ElementDefinition(10, "Time", "C", "TM", 4, 8),
        ElementDefinition(11, "Request Reference Number", "O", "AN", 1, 45),
        ElementDefinition(12, "Assigned Identification", "O", "AN", 1, 20),
    ],
    "SDQ": [
        ElementDefinition(1, "Unit or Basis for Measurement Code", "M", "ID", 2, 2),
        ElementDefinition(2, "Identification Code Qualifier", "O", "ID", 1, 2),
        ElementDefinition(3, "Identification Code", "M", "AN", 2, 80),
        ElementDefinition(4, "Quantity", "M", "R", 1, 15),
        ElementDefinition(5, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(6, "Quantity", "C", "R", 1, 15),
        ElementDefinition(7, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(8, "Quantity", "C", "R", 1, 15),
        ElementDefinition(9, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(10, "Quantity", "C", "R", 1, 15),
        ElementDefinition(11, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(12, "Quantity", "C", "R", 1, 15),
        ElementDefinition(13, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(14, "Quantity", "C", "R", 1, 15),
        ElementDefinition(15, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(16, "Quantity", "C", "R", 1, 15),
        ElementDefinition(17, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(18, "Quantity", "C", "R", 1, 15),
        ElementDefinition(19, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(20, "Quantity", "C", "R", 1, 15),
        ElementDefinition(21, "Identification Code", "C", "AN", 2, 80),
        ElementDefinition(22, "Quantity", "C", "R", 1, 15),
        ElementDefinition(23, "Location Identifier", "O", "AN", 1, 30),
    ],
    "SLN": [
        # SLN05 (Composite Unit of Measure) is a composite -- left out. Stops
        # at SLN-10 -- SLN-11 through SLN-28 repeats the same qualifier/ID pair.
        ElementDefinition(1, "Assigned Identification", "M", "AN", 1, 20),
        ElementDefinition(2, "Assigned Identification", "O", "AN", 1, 20),
        ElementDefinition(3, "Relationship Code", "M", "ID", 1, 1),
        ElementDefinition(4, "Quantity", "C", "R", 1, 15),
        ElementDefinition(6, "Unit Price", "C", "R", 1, 17),
        ElementDefinition(7, "Basis of Unit Price Code", "O", "ID", 2, 2),
        ElementDefinition(8, "Relationship Code", "O", "ID", 1, 1),
        ElementDefinition(9, "Product/Service ID Qualifier", "C", "ID", 2, 2),
        ElementDefinition(10, "Product/Service ID", "C", "AN", 1, 80),
    ],
    "SV1": [
        # SV101 (Composite Medical Procedure Identifier) is a composite -- left out.
        ElementDefinition(2, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(3, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(4, "Quantity", "C", "R", 1, 15),
        ElementDefinition(5, "Facility Code Value", "O", "AN", 1, 3),
        ElementDefinition(6, "Industry Code", "O", "AN", 1, 30),
        ElementDefinition(7, "Diagnosis Code Pointer", "O", "N0", 1, 2),
        ElementDefinition(8, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(9, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(10, "Multiple Procedure Code", "O", "ID", 1, 2),
        ElementDefinition(11, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(12, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(13, "Review Code", "O", "ID", 1, 2),
        ElementDefinition(14, "National or Local Assigned Review Value", "O", "AN", 1, 2),
        ElementDefinition(15, "Copay Status Code", "O", "ID", 1, 1),
        ElementDefinition(16, "Health Care Professional Shortage Area Code", "O", "ID", 1, 1),
        ElementDefinition(17, "Reference Identification", "O", "AN", 1, 80),
        ElementDefinition(18, "Postal Code", "O", "ID", 3, 15),
        ElementDefinition(19, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(20, "Level of Care Code", "O", "ID", 1, 1),
        ElementDefinition(21, "Provider Agreement Code", "O", "ID", 1, 1),
    ],
    "SV2": [
        # SV202 (Composite Medical Procedure Identifier) is a composite -- left out.
        ElementDefinition(1, "Product/Service ID", "C", "AN", 1, 80),
        ElementDefinition(3, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(4, "Unit or Basis for Measurement Code", "C", "ID", 2, 2),
        ElementDefinition(5, "Quantity", "C", "R", 1, 15),
        ElementDefinition(6, "Unit Rate", "O", "R", 1, 10),
        ElementDefinition(7, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(8, "Yes/No Condition or Response Code", "O", "ID", 1, 1),
        ElementDefinition(9, "Nursing Home Residential Status Code", "O", "ID", 1, 1),
        ElementDefinition(10, "Level of Care Code", "O", "ID", 1, 1),
    ],
    "SVC": [
        # SVC01/SVC06 (Composite Medical Procedure Identifier) are composites -- left out.
        ElementDefinition(2, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(3, "Monetary Amount", "O", "R", 1, 18),
        ElementDefinition(4, "Product/Service ID", "O", "AN", 1, 80),
        ElementDefinition(5, "Quantity", "O", "R", 1, 15),
        ElementDefinition(7, "Quantity", "O", "R", 1, 15),
    ],
    "TA1": [
        ElementDefinition(1, "Interchange Control Number", "M", "N0", 9, 9),
        ElementDefinition(2, "Interchange Date", "M", "DT", 6, 6),
        ElementDefinition(3, "Interchange Time", "M", "TM", 4, 4),
        ElementDefinition(4, "Interchange Acknowledgment Code", "M", "ID", 1, 1),
        ElementDefinition(5, "Interchange Note Code", "M", "ID", 3, 3),
    ],
}

#: The X12 release/version this whole reference targets. Every segment and
#: element definition here is 004010 -- a later release can rename or
#: resize a position, so this isn't assumed to hold if the project ever
#: adds a second release's worth of definitions.
RELEASE = "004010"

#: segment_id -> where its element breakdown came from. Segments not listed
#: here predate this tracking (curated by hand against DLA convention PDFs
#: and general X12 004010 knowledge, not scraped from any one site).
_SOURCES: dict[str, str] = {
    sid: "Stedi"
    for sid in (
        "ACK", "AK1", "AK2", "AK3", "AK4", "AK5", "AK9", "B10", "B2", "B2A",
        "BCH", "BGN", "BIG", "CAD", "CLM", "CLP", "COB", "CSH", "CTX", "CUR",
        "ENT", "G61", "G62", "G72", "HD", "IK3", "IK4", "IK5", "IT1", "IT3",
        "ITA", "K3", "L11", "L3", "LIN", "LUI", "LX", "MAN", "MSG", "N2",
        "NTE", "PLB", "PO4", "POC", "PRF", "PRV", "PWK", "RMR", "S5", "SCH",
        "SDQ", "SLN", "SV1", "SV2", "SVC", "TA1",
    )
}


def element_source(segment_id: str) -> str:
    """Where ``segment_id``'s element breakdown came from -- "Stedi" for the
    2026 backfill, "x12-tools" (hand-curated) for everything earlier."""
    return _SOURCES.get(segment_id, "x12-tools")
