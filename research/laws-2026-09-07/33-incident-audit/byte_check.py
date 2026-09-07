# Re-derive, from the shipped engine law, every byte->ruling pair claimed in
# this session's coordinator logs (FINDINGS.md, ATTACK_FINDINGS.md) and in
# tests/test_law_never_ruled_wrong.py. Nothing here is taken on trust.
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.engine import decide, situation, BITS, ACTS

# (label, raw byte as claimed, act claimed for it)
CLAIMS = [
    # ATTACK_FINDINGS.md
    ("07 byte passed 513",  513, "SHIP"),
    ("07 byte owed   515",  515, "ADD_STATE"),
    ("01 delivered   513",  513, "SHIP"),
    ("01 owed        517",  517, "ADD_MATERIAL"),
    ("08 delivered   513",  513, "SHIP"),
    ("08 measured    545",  545, "RAISE_BUDGET"),
    ("02 delivered 0x201", 0x201, "SHIP"),
    ("02 owed      0x203", 0x203, "ADD_STATE"),
    ("03 passed    0x201", 0x201, "SHIP"),
    ("03 supported 0x203", 0x203, "ADD_STATE"),
    ("05 passed      513",  513, "SHIP"),
    ("04 byte      0x201", 0x201, "SHIP"),
    ("09 byte        513",  513, "SHIP"),
    ("09 correct     515",  515, "ADD_STATE"),
    # FINDINGS.md
    ("04L byte 0x201",     0x201, "SHIP"),
    ("04L byte 0x203",     0x203, "ADD_STATE"),
    ("06L byte 0x21",       0x21, "RAISE_BUDGET"),
    ("01L byte 0 (UNREAD-owed situation packed as no-blocker)", 0, "SHIP"),
]

# the same, expressed as keyword observations (the form the body uses)
KW = [
    ("BUILT",                    dict(BUILT=True),                "SHIP"),
    ("BUILT+AMB",                dict(BUILT=True, AMB=True),      "ADD_STATE"),
    ("BUILT+UNREAD",             dict(BUILT=True, UNREAD=True),   "ADD_MATERIAL"),
    ("BUILT+CAPPED",             dict(BUILT=True, CAPPED=True),   "RAISE_BUDGET"),
    ("CAPPED",                   dict(CAPPED=True),               "RAISE_BUDGET"),
    ("REFUTED",                  dict(REFUTED=True),              "HARVEST_COUNTEREXAMPLE"),
    ("REFUTED+HIDDEN",           dict(REFUTED=True, HIDDEN=True), "CHANGE_GRANULARITY"),
    ("UNREAD",                   dict(UNREAD=True),               "ADD_MATERIAL"),
    ("HIDDEN",                   dict(HIDDEN=True),               "CHANGE_GRANULARITY"),
    ("BUILT+SELF",               dict(BUILT=True, SELF=True),     "SHIP"),
    ("empty",                    dict(),                          "SHIP"),
]

bad = 0
print("== raw bytes claimed in the session logs ==")
for label, x, claimed in CLAIMS:
    got = decide(x)
    ok = "OK " if got == claimed else "MISMATCH"
    if got != claimed:
        bad += 1
    print(f"{ok} {label:<58} decide({x}) = {got}   (claimed {claimed})")

print("\n== the same situations packed through situation(**obs) ==")
for label, obs, claimed in KW:
    s = situation(**obs)
    got = decide(s)
    ok = "OK " if got == claimed else "MISMATCH"
    if got != claimed:
        bad += 1
    print(f"{ok} {label:<26} situation={s:<5} decide = {got}   (claimed {claimed})")

print("\n== bit->byte identities the logs assert ==")
for name in ("BUILT", "AMB", "UNREAD", "CAPPED"):
    print(f"situation({name}=True) = {situation(**{name: True})}")
print(f"situation(BUILT=True, AMB=True)    = {situation(BUILT=True, AMB=True)}")
print(f"situation(BUILT=True, UNREAD=True) = {situation(BUILT=True, UNREAD=True)}")
print(f"situation(BUILT=True, CAPPED=True) = {situation(BUILT=True, CAPPED=True)}")

print(f"\nmismatches: {bad}")
