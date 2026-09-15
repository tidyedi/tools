# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Michael Schertz
"""Tests against crafted layout-text fixtures shaped like real DLA IC output
(validated against 004010F511M5MA62 during development) -- not against an
actual PDF, so these don't depend on poppler being installed."""

from __future__ import annotations

from x12_tools.convention_pdf import (
    _parse_segment_details,
    _parse_segment_table,
    _strip_running_header_footer,
)


def test_strip_running_header_footer_removes_repeated_boilerplate() -> None:
    def page(n: int) -> str:
        return (
            "DLMS Implementation Convention (IC) 511M -      ADC 59, 69A\n"
            "Requisition Modification                        375, 377\n"
            f"  - unique content only found on page {n}\n"
            f"004010F511M5MA62                     {n}                     April 24, 2026"
        )

    text = "\x0c".join(page(n) for n in (1, 2, 3))
    cleaned = _strip_running_header_footer(text)

    assert "DLMS Implementation Convention" not in cleaned
    assert "004010F511M5MA62" not in cleaned
    # real, page-specific content must survive on every page
    for n in (1, 2, 3):
        assert f"unique content only found on page {n}" in cleaned


def test_parse_segment_table_tracks_loop_context_and_wrapped_names() -> None:
    lines = """
Heading:
   Pos          Id        Segment Name                           Req         Max Use           Repeat           Notes                 Usage
   10           ST        Transaction Set Header                   M             1                                                  Must use
   20           BR        Beginning Segment for Material           M             1                                                  Must use
                          Management
 * 40           NTE       Note/Special Instruction                 O             10                                                 Not Used
   LOOP ID - LM                                                                                  50            N1/50L
   50           LM        Code Source Information                  O             1                              N1/50                Used
   60           LQ        Industry Code                            M            100                                                 Must use
 * LOOP ID - LM
 * 70           LM        Nested Flagged Loop Example              O             1                                                 Not Used
Notes:
""".splitlines()

    rows = _parse_segment_table(lines)
    by_pos = {r.pos: r for r in rows}

    assert by_pos["10"].segment_id == "ST"
    # the wrapped continuation line joins back onto the segment name
    assert by_pos["20"].name == "Beginning Segment for Material Management"
    assert by_pos["40"].flagged is True
    assert by_pos["40"].loop_id is None
    assert by_pos["50"].loop_id == "LM"
    assert by_pos["50"].notes == "N1/50"
    assert by_pos["60"].requirement == "M"
    # a starred "LOOP ID" marker is still recognized as a loop, not a segment row
    assert by_pos["70"].loop_id == "LM"
    assert by_pos["70"].flagged is True


def test_parse_segment_details_keeps_codes_across_an_interrupting_dlms_note() -> None:
    lines = """
                                                                                                                 Pos: 20                          Max: 1
BR Beginning Segment for Material                                                                                          Heading - Mandatory
Management
                                                                                                                 Loop: N/A                 Elements: 1

Element Summary:
   Ref             Id         Element Name                                                Req        Type        Min/Max                 Usage
   BR01            353        Transaction Set Purpose Code                                 M          ID             2/2                Must use

                              Description: Code identifying purpose of
                              transaction set

                              Code Name
                              00     Original
                              77     Simulation Exercise
                              DLMS Note:
                              1. Activities initiating simulated exercises must
                                 coordinate carefully.

                              ZZ     Mutually Defined
""".splitlines()

    details = _parse_segment_details(lines)

    assert "BR" in details
    assert details["BR"].pos == "20"
    br01 = details["BR"].elements[0]
    assert br01.ref == "BR01"
    assert br01.data_type == "ID"
    codes = {c.code: c.name for c in br01.codes}
    # the DLMS Note between "77" and "ZZ" must not truncate the code list
    assert codes == {"00": "Original", "77": "Simulation Exercise", "ZZ": "Mutually Defined"}


def test_parse_segment_details_never_attaches_codes_to_a_non_id_element() -> None:
    # A two-column DLA PDF's text extraction has no notion of the source
    # PDF's visual columns, so a code list can end up interleaved after a
    # later, uncoded element's own row instead of right after the ID-type
    # element it actually belongs to. Here N901 is the real ID-type owner,
    # but the code list appears after N904 (Date, a DT-type element that can
    # never legitimately have one) -- it must not get attached to N904.
    lines = """
                                                                                                                 Pos: 30                          Max: 1
N9 Extended Reference Information                                                                                          Heading - Used

Element Summary:
   Ref             Id         Element Name                                                Req        Type        Min/Max                 Usage
   N901            128        Reference Identification Qualifier                          M          ID             2/3                Must use
   N904            373        Date                                                         O          DT             8/8                   Used

                              Code Name
                              ON     Attached To
                              BT     Batch Number
""".splitlines()

    details = _parse_segment_details(lines)

    n904 = next(e for e in details["N9"].elements if e.ref == "N904")
    assert n904.data_type == "DT"
    assert n904.codes == []
