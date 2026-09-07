#!/usr/bin/env python
"""08-engine-monotonicity: exhaustive bit-flip property test of the engine law.

Question: can adding ONE evidence bit ever move a ruling from a refusal
(any act other than SHIP) to SHIP?  Enumerates all 1024 single-bit-add
pairs (x, x|bit) over the 256 situations, all 6305 proper superset pairs,
and checks job-invariance (bits 8-9) so the answer does not depend on the
DEBUG job fluidfix always runs as.

Run:  nice -n 15 timeout 300 .venv/bin/python monotonicity.py
"""
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import ACTS, BITS, decide, situation  # noqa: E402

SHIP = "SHIP"


def byte_to_kwargs(x: int) -> dict:
    return {b: bool((x >> i) & 1) for i, b in enumerate(BITS)}


def name(x: int) -> str:
    on = [b for i, b in enumerate(BITS) if (x >> i) & 1]
    return "+".join(on) if on else "(empty)"


def rule(x: int) -> str:
    """The law's ruling on the 8-bit observation byte, via the shipped API."""
    return decide(situation(**byte_to_kwargs(x)))


# --- closed form read off the formula (derivation in REPORT.md) -----------
def spec(x: int) -> str:
    low = x & 0x7E                      # bits 1..6: AMB UNREAD NOTWIN HIDDEN CAPPED REFUTED
    second = (low & -low).bit_length() - 1 if low else 0
    first = 4 if ((x & 15) in (7, 8) and (x & 240)) else 0
    return ACTS[(first + second) % 8]


def main() -> None:
    out = []
    p = out.append

    table = {x: rule(x) for x in range(256)}

    # 1. closed form vs the vendored formula, all 256
    mism = [x for x in range(256) if spec(x) != table[x]]
    p(f"closed-form vs decide(): {256 - len(mism)}/256 agree; mismatches={mism}")

    # 2. job invariance: feed the raw 10-bit word (job in bits 8-9) to decide()
    job_diff = [(x, j) for j in range(4) for x in range(256)
                if decide(x | (j << 8)) != table[x]]
    p(f"job-invariance (bits 8-9 = 0..3) vs job=2: {1024 - len(job_diff)}/1024 agree; "
      f"differ={job_diff[:8]}")

    # 3. the SHIP set
    ships = [x for x in range(256) if table[x] == SHIP]
    p(f"situations ruling SHIP: {len(ships)}/256 -> " + ", ".join(name(x) for x in ships))
    p("act histogram over 256: " + ", ".join(
        f"{a}={c}" for a, c in sorted(Counter(table.values()).items(),
                                       key=lambda kv: ACTS.index(kv[0]))))

    # 4. all single-bit-ADD pairs
    pairs = [(x, x | (1 << b), b) for x in range(256) for b in range(8)
             if not (x >> b) & 1]
    assert len(pairs) == 1024
    kinds = Counter()
    ref_to_ship, ship_to_ship, ship_to_ref, ref_to_other = [], [], [], []
    per_bit_changes = Counter()
    for x, y, b in pairs:
        a0, a1 = table[x], table[y]
        if a0 != a1:
            per_bit_changes[BITS[b]] += 1
        if a0 != SHIP and a1 == SHIP:
            kinds["refusal->SHIP"] += 1; ref_to_ship.append((x, y, b))
        elif a0 == SHIP and a1 == SHIP:
            kinds["SHIP->SHIP"] += 1; ship_to_ship.append((x, y, b))
        elif a0 == SHIP and a1 != SHIP:
            kinds["SHIP->refusal"] += 1; ship_to_ref.append((x, y, b))
        elif a0 == a1:
            kinds["refusal->same refusal"] += 1
        else:
            kinds["refusal->different refusal"] += 1; ref_to_other.append((x, y, b))
    p("single-bit-add pairs (1024): " + ", ".join(f"{k}={v}" for k, v in kinds.items()))
    p("pairs whose act changes, by bit added: " + ", ".join(
        f"{b}={per_bit_changes[b]}" for b in BITS))

    p("")
    p("refusal->SHIP pairs (THE QUESTION):")
    if not ref_to_ship:
        p("  NONE (0 of 1024)")
    for x, y, b in ref_to_ship:
        p(f"  {name(x)} [{table[x]}] +{BITS[b]} -> {name(y)} [{table[y]}]")

    p("")
    p("SHIP->SHIP pairs (adding a bit keeps SHIP):")
    for x, y, b in ship_to_ship:
        p(f"  {name(x)} +{BITS[b]} -> {name(y)}  [SHIP stays SHIP]")

    p("")
    p("SHIP->refusal pairs (adding a bit withdraws SHIP):")
    for x, y, b in ship_to_ref:
        p(f"  {name(x)} +{BITS[b]} -> {table[y]}")

    p("")
    p("refusal->DIFFERENT refusal pairs (act changes, SHIP not involved):")
    by_reason = defaultdict(list)
    for x, y, b in ref_to_other:
        first_x = (x & 15) in (7, 8) and (x & 240)
        first_y = (y & 15) in (7, 8) and (y & 240)
        why = ("first-term(+4) toggled" if bool(first_x) != bool(first_y)
               else "lower-precedence bit added")
        by_reason[why].append((x, y, b))
    for why, lst in by_reason.items():
        p(f"  [{why}] {len(lst)} pairs")
        for x, y, b in lst:
            p(f"    {name(x)} [{table[x]}] +{BITS[b]} -> [{table[y]}]")

    # 5. superset closure: adding ANY set of bits to a refusal never reaches SHIP
    sup_viol = []
    n_sup = 0
    for x in range(256):
        if table[x] == SHIP:
            continue
        free = [b for b in range(8) if not (x >> b) & 1]
        for m in range(1, 1 << len(free)):
            y = x
            for i, b in enumerate(free):
                if (m >> i) & 1:
                    y |= 1 << b
            n_sup += 1
            if table[y] == SHIP:
                sup_viol.append((x, y))
    p("")
    p(f"superset closure from every refusal ({n_sup} proper supersets): "
      f"{len(sup_viol)} reach SHIP")

    # 6. algebraic statement
    alg = all((table[x] == SHIP) == ((x & 0x7E) == 0) for x in range(256))
    p(f"SHIP <=> (x & 0x7E)==0, i.e. none of AMB/UNREAD/NOTWIN/HIDDEN/CAPPED/REFUTED set: "
      f"{'holds on all 256' if alg else 'FAILS'}")

    # 7. the family the body can present at the shipping call site
    #    (loop.py:217: BUILT=True, AMB=..., CAPPED=...)
    p("")
    p("body-reachable family at loop.py:217 (BUILT always true; AMB, CAPPED measured):")
    for amb in (0, 1):
        for capped in (0, 1):
            x = 1 | (amb << 1) | (capped << 5)
            p(f"  {name(x):22s} -> {table[x]}")
    p("what the same site would rule if HIDDEN were carried in the byte:")
    for amb in (0, 1):
        for capped in (0, 1):
            x = 1 | (amb << 1) | (1 << 4) | (capped << 5)
            p(f"  {name(x):29s} -> {table[x]}")

    # 8. every single-bit REMOVAL that lands on SHIP (same pairs, read backwards)
    p("")
    p("refusals one bit-removal away from SHIP:")
    for x, y, b in ship_to_ref:
        p(f"  {name(y)} [{table[y]}] -{BITS[b]} -> {name(x)} [SHIP]")

    text = "\n".join(out)
    print(text)
    with open(__file__.replace("monotonicity.py", "monotonicity.out"), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
