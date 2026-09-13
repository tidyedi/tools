# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Segment ID -> standard X12 segment name, for pre-filling the "Segment
name" column of the convention table.

A segment's *name* (as opposed to what any one element inside it means) is
part of the ANSI X12 segment dictionary and doesn't change by release or by
which transaction set uses it -- ``N1`` is "Party Identification" whether it
shows up in an 850 or an 837. That makes a flat, static ``segment_id -> name``
table the right shape here: no version, no transaction-set context needed.

Sourced from the public X12 segment reference (cross-checked against
https://www.stedi.com/edi/x12/segment/<ID> for the entries below). Covers the
segments most commonly seen across the widely used transaction sets (850,
855, 856, 810, 820, 824, 830, 834, 835, 837, 997/999, 214, 204, and others) --
not exhaustive of the full X12 dictionary (which runs into the hundreds).
An ID not in this table just means the "Segment name" cell starts blank, the
same as for a name looked up in error -- either way it's editable.
"""

from __future__ import annotations

SEGMENT_NAMES: dict[str, str] = {
    # Envelope
    "ISA": "Interchange Control Header",
    "IEA": "Interchange Control Trailer",
    "GS": "Functional Group Header",
    "GE": "Functional Group Trailer",
    "ST": "Transaction Set Header",
    "SE": "Transaction Set Trailer",
    "TA1": "Interchange Acknowledgment",
    # Common across many transaction sets
    "BEG": "Beginning Segment for Purchase Order",
    "BAK": "Beginning Segment for Purchase Order Acknowledgment",
    "BSN": "Beginning Segment for Ship Notice",
    "BIG": "Beginning Segment for Invoice",
    "BGN": "Beginning Segment",
    "BCH": "Beginning Segment for Purchase Order Change",
    "BPO": "Beginning Segment for Blanket Purchase Order",
    "AK1": "Functional Group Response Header",
    "AK2": "Transaction Set Response Header",
    "AK3": "Data Segment Note",
    "AK4": "Data Element Note",
    "AK5": "Transaction Set Response Trailer",
    "AK9": "Functional Group Response Trailer",
    "N1": "Party Identification",
    "N2": "Additional Name Information",
    "N3": "Party Location",
    "N4": "Geographic Location",
    "N9": "Reference Identification",
    "NM1": "Individual or Organizational Name",
    "NX1": "Property Location",
    "PER": "Administrative Communications Contact",
    "REF": "Reference Identification",
    "DTM": "Date/Time Reference",
    "DTP": "Date or Time or Period",
    "AMT": "Monetary Amount",
    "QTY": "Quantity",
    "CUR": "Currency",
    "MSG": "Message Text",
    "NTE": "Note/Special Instruction",
    "PWK": "Paperwork",
    "TD1": "Carrier Details (Quantity and Weight)",
    "TD3": "Carrier Details (Equipment)",
    "TD4": "Carrier Details (Special Handling, or Hazardous Materials, or Both)",
    "TD5": "Carrier Details (Routing Sequence/Transit Time)",
    "FOB": "F.O.B. Related Instructions",
    "ITD": "Terms of Sale/Deferred Terms of Sale",
    "PID": "Product/Item Description",
    "MEA": "Measurements",
    "PO4": "Item Physical Details",
    "SAC": "Service, Promotion, Allowance, or Charge Information",
    "CTT": "Transaction Totals",
    "CTP": "Pricing Information",
    "SLN": "Subline Item Detail",
    "LIN": "Item Identification",
    "K3": "File Information",
    "L11": "Business Instructions and Reference Number",
    "LX": "Assigned Number",
    "MAN": "Marks and Numbers",
    "G61": "Contact",
    "G62": "Date/Time",
    "G72": "Allowance or Charge",
    # 850 / 855 / 860 purchase orders
    "POC": "Line Item Change",
    "IT1": "Baseline Item Data (Invoice)",
    "IT3": "Additional Item Data",
    "PO1": "Baseline Item Data",
    "SCH": "Line Item Schedule",
    "CSH": "Sales Requirements",
    "SDQ": "Destination Quantity",
    "ACK": "Line Item Acknowledgment",
    # 856 advance ship notice
    "HL": "Hierarchical Level",
    "PRF": "Purchase Order Reference",
    # 810 invoice
    "ITA": "Allowance, Charge or Service",
    "TXI": "Tax Information",
    "CAD": "Carrier Detail",
    # 820 payment order / remittance
    "TRN": "Trace",
    "BPR": "Beginning Segment for Payment Order/Remittance Advice",
    "ENT": "Entity",
    "RMR": "Remittance Advice Accounts Receivable Open Item Reference",
    # 834 benefit enrollment
    "INS": "Insured Benefit",
    "HD": "Health Coverage",
    "DBP": "Disability Benefit",
    "COB": "Coordination of Benefits",
    "LUI": "Language Use",
    # 835 remittance advice
    "CLP": "Claim Payment Information",
    "CAS": "Claims Adjustment",
    "SVC": "Service Payment Information",
    "PLB": "Provider Level Adjustment",
    # 837 healthcare claim
    "CLM": "Claim Information",
    "SV1": "Professional Service",
    "SV2": "Institutional Service Line",
    "HI": "Health Care Diagnosis Code",
    "PRV": "Provider Information",
    "SBR": "Subscriber Information",
    # 214 / 204 transportation
    "B10": "Beginning Segment for Transportation Carrier Shipment Status Message",
    "L3": "Total Weight and Charges",
    "S5": "Stop Off Details",
    "B2": "Beginning Segment for Shipment Information Transaction",
    "B2A": "Set Purpose",
    # 997 / 999 acknowledgments
    "IK5": "Transaction Set Response Trailer",
    "IK3": "Error Identification",
    "IK4": "Implementation Data Element Note",
    "CTX": "Context",
}
