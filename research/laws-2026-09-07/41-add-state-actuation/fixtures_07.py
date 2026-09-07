"""12 fixtures for attack 07-compensating-one-site.

Each fixture is a tiny, self-contained Python repo:

    <module>      one function; ONE line is the defect line
    test_*.py     a plausible, non-tautological suite (concrete value asserts)

The fixtures come in SIX PAIRS. Inside a pair the DEFECT LINE and the SUITE
are byte-identical; only which of the two suite-passing programs is the
PRISTINE one differs. That is the whole point: fluidfix's choice between the
two greens is therefore provably independent of which one is correct.

Each fixture is engineered so that, at the ONE defect line, two DIFFERENT
acts each produce a suite-passing candidate:

    kind emission order (lanes.EMIT, lowest live bit first):
        0 strictness  1 literal-off-by-one  2 swapped-return-operands
        3 flipped-additive  8 minmax-swap  10 flipped-comparison-direction
        11 reversed-minus-operands

`probe` is a call whose value DIFFERS between the two green programs — the
proof that they are two programs, not two spellings of one.
"""

FIXTURES = [
    # ---- pair A: array index (kind 1) vs strictness (kind 0) --------------
    dict(
        name="A1_index_vs_strict__pristine_is_index",
        module="gate.py",
        head='"""Reading gate: does the FIRST reading exceed the limit?"""\n\n\ndef alarm(readings, limit):\n',
        pristine="    return readings[0] > limit",
        defect="    return readings[1] > limit",
        tests=(
            "from gate import alarm\n\n\n"
            "def test_first_reading_at_limit_is_above():\n"
            "    assert alarm([7, 3], 3) is True\n\n\n"
            "def test_first_reading_below_limit():\n"
            "    assert alarm([1, 0], 5) is False\n\n\n"
            "def test_first_reading_clearly_above():\n"
            "    assert alarm([9, 8], 2) is True\n"
        ),
        probe="alarm([9, 1], 5)",
    ),
    dict(
        name="A2_index_vs_strict__pristine_is_strict",
        module="gate.py",
        head='"""Reading gate: is the SECOND reading at or above the limit?"""\n\n\ndef alarm(readings, limit):\n',
        pristine="    return readings[1] >= limit",
        defect="    return readings[1] > limit",
        tests=(
            "from gate import alarm\n\n\n"
            "def test_first_reading_at_limit_is_above():\n"
            "    assert alarm([7, 3], 3) is True\n\n\n"
            "def test_first_reading_below_limit():\n"
            "    assert alarm([1, 0], 5) is False\n\n\n"
            "def test_first_reading_clearly_above():\n"
            "    assert alarm([9, 8], 2) is True\n"
        ),
        probe="alarm([9, 1], 5)",
    ),

    # ---- pair B: float threshold (kind 1) vs strictness (kind 0) ----------
    dict(
        name="B1_threshold_vs_strict__pristine_is_literal",
        module="parcel.py",
        head='"""Parcel surcharge. weight_kg is a float (scales report grams)."""\n\n\ndef surcharge(weight_kg):\n',
        pristine="    return weight_kg > 20",
        defect="    return weight_kg > 21",
        tests=(
            "from parcel import surcharge\n\n\n"
            "def test_heavy_parcel():\n"
            "    assert surcharge(30.0) is True\n\n\n"
            "def test_light_parcel():\n"
            "    assert surcharge(10.0) is False\n\n\n"
            "def test_just_over_the_line():\n"
            "    assert surcharge(21.0) is True\n"
        ),
        probe="surcharge(20.5)",
    ),
    dict(
        name="B2_threshold_vs_strict__pristine_is_strict",
        module="parcel.py",
        head='"""Parcel surcharge. weight_kg is a float (scales report grams)."""\n\n\ndef surcharge(weight_kg):\n',
        pristine="    return weight_kg >= 21",
        defect="    return weight_kg > 21",
        tests=(
            "from parcel import surcharge\n\n\n"
            "def test_heavy_parcel():\n"
            "    assert surcharge(30.0) is True\n\n\n"
            "def test_light_parcel():\n"
            "    assert surcharge(10.0) is False\n\n\n"
            "def test_just_over_the_line():\n"
            "    assert surcharge(21.0) is True\n"
        ),
        probe="surcharge(20.5)",
    ),

    # ---- pair C: slice bound (kind 1) vs strictness (kind 0) --------------
    dict(
        name="C1_slice_vs_strict__pristine_is_slice",
        module="report.py",
        head='"""Budget report."""\n\n\ndef over_budget(values, threshold):\n',
        pristine="    return sum(values[0:]) > threshold",
        defect="    return sum(values[1:]) > threshold",
        tests=(
            "from report import over_budget\n\n\n"
            "def test_exactly_on_budget():\n"
            "    assert over_budget([3, 4], 7) is False\n\n\n"
            "def test_tail_alone_is_over():\n"
            "    assert over_budget([0, 10], 9) is True\n\n\n"
            "def test_total_is_over():\n"
            "    assert over_budget([5, 9], 9) is True\n\n\n"
            "def test_well_under():\n"
            "    assert over_budget([2, 1], 8) is False\n"
        ),
        probe="over_budget([6, 2], 5)",
    ),
    dict(
        name="C2_slice_vs_strict__pristine_is_strict",
        module="report.py",
        head='"""Budget report."""\n\n\ndef over_budget(values, threshold):\n',
        pristine="    return sum(values[1:]) >= threshold",
        defect="    return sum(values[1:]) > threshold",
        tests=(
            "from report import over_budget\n\n\n"
            "def test_exactly_on_budget():\n"
            "    assert over_budget([3, 4], 7) is False\n\n\n"
            "def test_tail_alone_is_over():\n"
            "    assert over_budget([0, 10], 9) is True\n\n\n"
            "def test_total_is_over():\n"
            "    assert over_budget([5, 9], 9) is True\n\n\n"
            "def test_well_under():\n"
            "    assert over_budget([2, 1], 8) is False\n"
        ),
        probe="over_budget([6, 2], 5)",
    ),

    # ---- pair D: minmax swap (kind 8) vs strictness (kind 0) --------------
    dict(
        name="D1_minmax_vs_strict__pristine_is_max",
        module="window.py",
        head='"""Admission window."""\n\n\ndef passes(a, b, limit):\n',
        pristine="    return max(a, b) > limit",
        defect="    return min(a, b) > limit",
        tests=(
            "from window import passes\n\n\n"
            "def test_one_side_over():\n"
            "    assert passes(5, 8, 5) is True\n\n\n"
            "def test_both_under():\n"
            "    assert passes(1, 2, 7) is False\n\n\n"
            "def test_both_over():\n"
            "    assert passes(9, 9, 3) is True\n"
        ),
        probe="passes(4, 10, 6)",
    ),
    dict(
        name="D2_minmax_vs_strict__pristine_is_min_ge",
        module="window.py",
        head='"""Admission window."""\n\n\ndef passes(a, b, limit):\n',
        pristine="    return min(a, b) >= limit",
        defect="    return min(a, b) > limit",
        tests=(
            "from window import passes\n\n\n"
            "def test_one_side_over():\n"
            "    assert passes(5, 8, 5) is True\n\n\n"
            "def test_both_under():\n"
            "    assert passes(1, 2, 7) is False\n\n\n"
            "def test_both_over():\n"
            "    assert passes(9, 9, 3) is True\n"
        ),
        probe="passes(4, 10, 6)",
    ),

    # ---- pair E: array index (kind 1) vs flipped additive (kind 3) --------
    dict(
        name="E1_index_vs_additive__pristine_is_index",
        module="payout.py",
        head='"""Payout."""\n\n\ndef total(values, bonus):\n',
        pristine="    return values[0] + bonus",
        defect="    return values[1] + bonus",
        tests=(
            "from payout import total\n\n\n"
            "def test_small_bonus():\n"
            "    assert total([5, 9], 2) == 7\n\n\n"
            "def test_no_bonus():\n"
            "    assert total([10, 10], 0) == 10\n\n\n"
            "def test_larger_bonus():\n"
            "    assert total([1, 7], 3) == 4\n"
        ),
        probe="total([1, 2], 1)",
    ),
    dict(
        name="E2_index_vs_additive__pristine_is_minus",
        module="payout.py",
        head='"""Payout."""\n\n\ndef total(values, bonus):\n',
        pristine="    return values[1] - bonus",
        defect="    return values[1] + bonus",
        tests=(
            "from payout import total\n\n\n"
            "def test_small_bonus():\n"
            "    assert total([5, 9], 2) == 7\n\n\n"
            "def test_no_bonus():\n"
            "    assert total([10, 10], 0) == 10\n\n\n"
            "def test_larger_bonus():\n"
            "    assert total([1, 7], 3) == 4\n"
        ),
        probe="total([1, 2], 1)",
    ),

    # ---- pair F: array index (kind 1) vs operand reversal (kind 2) --------
    dict(
        name="F1_index_vs_reversal__pristine_is_index",
        module="offsetcalc.py",
        head='"""Offset adjustment."""\n\n\ndef adjust(items, offset):\n',
        pristine="    return items[0] - offset",
        defect="    return items[1] - offset",
        tests=(
            "from offsetcalc import adjust\n\n\n"
            "def test_offset_above_item():\n"
            "    assert adjust([1, 7], 4) == -3\n\n\n"
            "def test_offset_equals_item():\n"
            "    assert adjust([5, 5], 5) == 0\n\n\n"
            "def test_larger_offset():\n"
            "    assert adjust([2, 10], 6) == -4\n"
        ),
        probe="adjust([3, 4], 1)",
    ),
    dict(
        name="F2_index_vs_reversal__pristine_is_reversed",
        module="offsetcalc.py",
        head='"""Offset adjustment."""\n\n\ndef adjust(items, offset):\n',
        pristine="    return offset - items[1]",
        defect="    return items[1] - offset",
        tests=(
            "from offsetcalc import adjust\n\n\n"
            "def test_offset_above_item():\n"
            "    assert adjust([1, 7], 4) == -3\n\n\n"
            "def test_offset_equals_item():\n"
            "    assert adjust([5, 5], 5) == 0\n\n\n"
            "def test_larger_offset():\n"
            "    assert adjust([2, 10], 6) == -4\n"
        ),
        probe="adjust([3, 4], 1)",
    ),
]
