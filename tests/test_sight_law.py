# SPDX-License-Identifier: AGPL-3.0-or-later
"""The SIGHT law, verified exhaustively — the Python port of sight.c must
agree with the authored specification on all 256 situations, and must obey
the two tier rules the law exists to make unrepresentable.

These are the same checks the authored sight.c runs in C. If the port ever
drifts from the kernel, this goes red.
"""
import pytest

from fluidfix.sight import BITS, observe_bits, sight, situation

FRAMED, SCARCE, LITERAL = 1 << 0, 1 << 1, 1 << 2
FAILONLY, NAMED, TOUCHED, SMALL = 1 << 3, 1 << 4, 1 << 5, 1 << 6
UBIQUITOUS = 1 << 7
POINTING_MASK = FRAMED | SCARCE | LITERAL


def spec(x):
    """The authored specification, transcribed from sight.c's self-check."""
    if x & 7:
        return 0
    if (x >> 3) & 1:
        return 2 + ((x >> 7) & 1)
    if (x >> 4) & 1:
        return 3 + ((x >> 7) & 1)
    if (x >> 5) & 1:
        return 4 + ((x >> 7) & 1)
    if (x >> 6) & 1:
        return 5 + ((x >> 7) & 1)
    return 6 + ((x >> 7) & 1)


def test_matches_specification_on_all_256_situations():
    wrong = [x for x in range(256) if sight(x) != spec(x)]
    assert wrong == []


def test_output_is_always_a_priority_0_to_7():
    assert all(0 <= sight(x) <= 7 for x in range(256))


def test_r1_pointing_outranks_every_non_pointing_file():
    """No quantity of circumstantial evidence closes the gap."""
    pointing = [x for x in range(256) if x & POINTING_MASK]
    plain = [x for x in range(256) if not x & POINTING_MASK]
    bad = [(a, b) for a in pointing for b in plain if not sight(a) < sight(b)]
    assert bad == []


def test_r2_ubiquitous_never_demotes_a_pointed_at_file():
    """The penalty is gated off algebraically, not by a comparison."""
    bad = [x for x in range(256)
           if x & POINTING_MASK and sight(x) != sight(x & 0x7F)]
    assert bad == []


def test_r2_ubiquitous_does_demote_among_circumstantial_files():
    """The penalty must still work where it is meant to — otherwise the
    gate would be trivially satisfied by disabling the lane."""
    assert sight(NAMED | UBIQUITOUS) > sight(NAMED)
    assert sight(0 | UBIQUITOUS) > sight(0)


def test_r3_monotone_in_the_evidence_bits():
    """Adding evidence is never worse (bit 7 is a penalty, not evidence)."""
    bad = []
    for x in range(256):
        for b in range(7):
            if not (x >> b) & 1 and sight(x | (1 << b)) > sight(x):
                bad.append((x, b))
    assert bad == []


# ---------------------------------------------------------- incidents ----
# Each is real and measured on click 8.5.1.

def test_incident_1_literal_alone_is_enough():
    """termui.py: the literal 95 occurred in 1 of 17 files and nothing else
    distinguished it. 1,740s REFUSED -> 50s byte-exact."""
    assert sight(LITERAL) == 0


def test_incident_2_scarce_beats_a_filename_coincidence():
    """types.py:499 — the defect file was UBIQUITOUS and unnamed, while
    NAMED fired for shell_completion.py. The taught class's own signal is
    what pointed at the truth."""
    assert sight(SCARCE | UBIQUITOUS) == 0
    assert sight(SCARCE | UBIQUITOUS) < sight(NAMED)
    # and the full observed situation, not just the isolated bits:
    types_py = SCARCE | UBIQUITOUS
    shell_completion_py = NAMED | SMALL | TOUCHED
    assert sight(types_py) < sight(shell_completion_py)


def test_incident_3_no_evidence_invents_no_winner():
    """_textwrap.py: genuinely undecidable. Every evidence-free file must
    land in the same class so the caller can report an honest search limit
    rather than a false lead."""
    assert sight(0) == 6
    evidence_free = {sight(x) for x in range(256)
                     if not x & POINTING_MASK and not x & 0x78}
    assert evidence_free == {6, 7}       # UBIQUITOUS splits 6/7, nothing else


# ------------------------------------------------- documented properties --

def test_the_three_pointing_bits_are_equal_rank():
    """Documented in sight.py: callers break these ties, not the law."""
    assert sight(FRAMED) == sight(SCARCE) == sight(LITERAL) == 0


def test_priority_one_is_never_emitted():
    """The spec steps 0 -> 2; the slot is reserved."""
    assert 1 not in {sight(x) for x in range(256)}


def test_observe_bits_and_situation_agree():
    assert observe_bits(scarce=True, ubiquitous=True) == SCARCE | UBIQUITOUS
    assert situation(SCARCE=True, UBIQUITOUS=True) == SCARCE | UBIQUITOUS
    assert len(BITS) == 8


def test_observe_bits_rejects_an_unmeasured_lane():
    with pytest.raises(TypeError):
        observe_bits(invented=True)
