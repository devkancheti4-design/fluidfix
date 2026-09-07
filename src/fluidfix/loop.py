# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""The repair loop: observations in, suite-accepted repair or honest refusal out.
(Byte-exactness is a measured property of the acts — 26/26 accepted repairs on
the benchmark corpus — not an enforced invariant; the suite is the judge.)

    for each observation:
        mask <- one bit per reported kind
        while not HALT(mask):
            kind <- EMIT(mask)              # fluid-router2, verbatim
            act  <- route(0, 5, kind)       # fluid-router, verbatim
            candidate <- apply(act, line, observation)
            unchanged?          -> NOPROGRESS: ADVANCE
            suite green?        -> repaired, stop
            else restore        -> ADVANCE

The output space is exactly {repair the suite accepts, refusal}. There is no
"plausible fix" branch: an empty mask halts, a kindless observation refuses,
and a green suite refuses before anything runs — searching without a failing
test has been measured to corrupt working code while reporting success.

File handling is byte-preserving: the source is split on "\\n" only (CRLF
lines keep their "\\r" as line content, form feeds stay inside lines so line
numbers match the tokenizer's), candidates re-attach the line's own ending,
and nothing is written back unless a candidate was actually tried.
"""
from __future__ import annotations

import json

import os
import subprocess
import time
from dataclasses import dataclass, field

from .acts import Observation, SpanEdit, act_for, candidates
from .engine import decide, situation
from .lanes import ADVANCE, EMIT, HALT, kind_of, mask_of
from .oracle import Oracle

__all__ = ["RepairResult", "repair"]


@dataclass
class RepairResult:
    repaired: bool
    refused: bool
    lineno: int | None = None
    old_line: str | None = None
    new_line: str | None = None
    acts_tried: list[int] = field(default_factory=list)
    suite_runs: int = 0
    seconds: float = 0.0
    reason: str = ""
    ambiguous: bool = False
    greens: list[str] = field(default_factory=list)   # all suite-passing candidates
    # CAPPED, as the engine law means it: the search was cut short, so what it
    # did not try is unknown. guard.py could not read this before 0.15.0 and
    # rebuilt its own byte without it, which dropped suite-passing candidates
    # and told the user every one had been rejected.
    capped: bool = False
    # the ruling the law returned for this search, verbatim. Every exit carries
    # one; a refusal without a ruling was this code deciding.
    ruling: str = ""
    # ADD_STATE, actuated: the pytest file that separates the ambiguous
    # candidates, generated from the greens already in memory. Empty when the
    # ruling was not ADD_STATE or the probe could not run.
    pinning_test: str = ""
    # Was AMB established by MEASURING whether the greens are different
    # programs, or only inferred from where they came from? False means the
    # differential probe could not run here — non-Python source is the common
    # case — so a SHIP from this search is not a proof of uniqueness.
    amb_measured: bool = True
    # the engine law's HARVEST_COUNTEREXAMPLE act, actuated: every rejected
    # candidate is kept WITH the failing test that rejected it
    tried_log: list = field(default_factory=list)
    tried_more: int = 0               # rejections beyond the 64-entry cap
    # provenance: the repair equals the git-HEAD content at that line (the
    # defect was an uncommitted edit); None when git/HEAD is unavailable
    restored_original: bool | None = None

    def summary(self) -> str:
        if self.repaired:
            return (f"repaired line {self.lineno} in {self.suite_runs} suite runs "
                    f"({self.seconds:.1f}s):\n  - {self.old_line.strip()}\n"
                    f"  + {self.new_line.strip()}")
        return f"refused: {self.reason} ({self.seconds:.1f}s)"


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


# ---------------------------------------------------------- crash safety --
# ROLLBACK MUST SURVIVE THE PROCESS DYING. Candidates are applied to the real
# file and rolled back from memory, which is byte-exact and correct — right up
# until the process is killed while a candidate is applied. Then the mutation
# stays on disk and nothing records what was there before.
#
# Measured 2026-09-04 on Box2D: a literal-off-by-one candidate turned an
# atomic increment into `+ 0` inside a worker spin loop. The test binary hung,
# every core went to 100% (load average 30), the guard was killed, and
# src/parallel_for.c was left holding fluidfix's mutation. Unattended on a
# studio's CI that is corrupted source with no audit trail.
#
# So the original bytes are journalled to .fluidfix/inflight.json before the
# first mutation and cleared after the final restore. A later run — or the
# same one restarting — puts the file back.
def _confirm_runs() -> int:
    """How many FINE records to take before trusting a coarse green.

    Each re-check is another fine-grained observation of the same candidate.
    When they disagree with the single-run verdict, the engine law's HIDDEN
    lane fires and rules CHANGE_GRANULARITY — a single run is the wrong
    granularity to judge at. Default 1. FLUIDFIX_CONFIRM=0 disables the lane
    (and restores the measured 14% false-accept rate on a flaky suite);
    higher values suit a suite you distrust."""
    try:
        return max(0, int(os.environ.get("FLUIDFIX_CONFIRM", "1")))
    except ValueError:
        return 1


def _journal_path(root: str) -> str:
    return os.path.join(root, ".fluidfix", "inflight.json")


def begin_inflight(root: str, rel: str, original: str) -> None:
    try:
        os.makedirs(os.path.join(root, ".fluidfix"), exist_ok=True)
        with open(_journal_path(root), "w", encoding="utf-8") as fh:
            json.dump({"file": rel, "original": original,
                       "started": time.time()}, fh)
    except OSError:
        pass                      # journalling is best-effort, never fatal


def end_inflight(root: str) -> None:
    try:
        os.remove(_journal_path(root))
    except OSError:
        pass


def recover_inflight(root: str) -> str | None:
    """Restore a file a killed run left mutated. Returns the path restored,
    or None. Safe to call on every start."""
    jp = _journal_path(root)
    if not os.path.exists(jp):
        return None
    try:
        with open(jp, encoding="utf-8") as fh:
            rec = json.load(fh)
        target = os.path.join(root, rec["file"])
        with open(target, "w", encoding="utf-8", newline="") as fh:
            fh.write(rec["original"])
    except (OSError, KeyError, ValueError):
        return None
    end_inflight(root)
    return rec.get("file")


def _restored_original(root: str, rel: str, lineno: int, new_line: str) -> bool | None:
    """Does the shipped repair equal the committed (HEAD) content at that
    line? None when git or the HEAD version is unavailable."""
    try:
        p = subprocess.run(["git", "-C", root, "show",
                            f"HEAD:{rel.replace(os.sep, '/')}"],
                           capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if p.returncode != 0:
        return None
    new = new_line.split("\n")
    return p.stdout.split("\n")[lineno - 1:lineno - 1 + len(new)] == new


def repair(oracle: Oracle, defect_file: str,
           observations: list[Observation],
           candidate_timeout: int | None = None,
           deadline: float | None = None) -> RepairResult:
    t0 = time.time()
    res = RepairResult(repaired=False, refused=True)
    path = os.path.join(oracle.root, defect_file)
    cand_t = candidate_timeout or oracle.timeout

    # PRECONDITION: a failing test. Without one the first candidate that leaves
    # the suite green is accepted — on a green suite that is the first
    # candidate tried, on whatever line it lands.
    if oracle.green():
        res.reason = "no failing test — nothing to repair"
        res.suite_runs = 1
        res.seconds = time.time() - t0
        return res
    res.suite_runs += 1

    with open(path, encoding="utf-8", newline="") as f:
        src = f.read()
    raw = src.split("\n")            # "\n".join(raw) == src, byte for byte
    tried: set[tuple[int, str]] = set()
    wrote = False

    # Journal the original bytes for the WHOLE call, not per observation.
    # First attempt scoped this to the first mutation window and discharged
    # it inside the per-kind loop; `wrote` stays True across iterations, so
    # every later mutation ran UNJOURNALLED — measured 2026-09-04, a hung
    # candidate in Box2D's parallel_for.c was left on disk with no journal.
    def _rule(capped: bool):
        """Ask the law with the situation AS MEASURED, and act on the ruling.

        EVERY exit from the search comes through here, including the ones where
        nothing went green. Before 0.15.0 this returned None when `greens` was
        empty and the caller printed a hardcoded refusal, so a refusal could
        never carry a ruling — measured on the C path as five refusals and zero
        rulings, and on the Python path as three refusals in ten reaching the
        law as an empty byte.

        The bits, and why each is measured this way:
          BUILT    a candidate passed the suite.
          AMB      one input carries two outputs.
          CAPPED   the search was cut short, so what it did not try is unknown.
          REFUTED  engine.py defines it as candidates were generated AND the
                   suite rejected EVERY ONE — so it needs `not greens`, not
                   merely a non-empty act list.
          UNREAD   the taught vocabulary named nothing at all. "A needed tool
                   reads nothing" is the docstring's own definition, and
                   ADD_MATERIAL is exactly what the old hardcoded text advised.
                   Measured as "nothing was ever generated to judge, and the
                   clock is not the reason". An observation may name kinds that
                   route to no applier at all (kinds 9 and 14 in
                   test_noop_acts_do_not_count_as_tried), which reads nothing
                   while naming something; and a search the deadline cut off
                   before its first candidate has read nothing YET, which is
                   CAPPED, not UNREAD. Both were byte 512 in a draft of this
                   change, and byte 512 rules SHIP with no green to ship.
        """
        sites = {g[3] for g in greens}
        # ---- AMB: measured on PROGRAM IDENTITY, not on provenance ---------
        # The law asks whether ONE INPUT CARRIES TWO OUTPUTS. Until 0.15.0 this
        # asked instead which candidate set a green came from and which line it
        # sat on, which is a different question and answered it wrongly in both
        # directions: 12 of 12 shipped and 6 wrong where two different programs
        # met at one line, and one program spelled twice refused as if it were
        # two. `differ` runs the two greens against inputs harvested from the
        # repo's own suite and looks for one they disagree on.
        amb_rec: dict = {}
        if len(greens) < 2:
            amb = False
        else:
            from .differ import programs_differ, UNKNOWN
            answer, amb_rec = programs_differ(
                oracle.root, defect_file, greens[0][3],
                [(g[3], g[0]) for g in greens],
                python=getattr(oracle, "python", None))
            if answer is UNKNOWN:
                # THE PROBE COULD NOT LOOK — a non-Python source, no enclosing
                # function, no seeds in the suite. Fall back to the older
                # provenance measure, and RECORD that identity was never
                # established so nothing downstream calls this repair unique.
                #
                # Refusing outright was tried first and is wrong: measured on
                # tests/test_java.py, the two greens are `units >= 10` and
                # `units > 9` — ONE PROGRAM SPELLED TWICE, which this code must
                # never call ambiguous. Blanket refusal turned a correct,
                # byte-exact Java repair into a denial.
                #
                # The gap is real and is not closed by this fallback: on
                # non-Python source the two shapes are indistinguishable here,
                # and the red team shipped 6 wrong repairs through exactly that
                # blind spot. Closing it means compiling and running both
                # candidates, which is the C/Java oracle's job, not ast's.
                amb = set_amb or len(sites) > 1
                res.amb_measured = False
                amb_rec["unmeasured"] = True
            else:
                amb = bool(answer)
        # TWO WAYS AN INPUT CARRIES TWO OUTPUTS, and both are real:
        #   set_amb   two greens inside ONE candidate set — the suite cannot
        #             tell two different programs apart at one site
        #             (K = 1 vs K = 2). This is the original AMB.
        #   sites>1   greens at DIFFERENT lines — two contradictory claims
        #             about where the fault is. Measured on Unity-shaped
        #             code: repairing a sign flip (line 32) and breaking
        #             Vec3's operator+ so the faults cancel (line 11) BOTH
        #             pass the suite.
        # What is NOT ambiguity: two SPELLINGS of one program reached by
        # different acts at one site — `units >= 10` and `units > 9` are the
        # same program written twice, and refusing those would refuse the
        # commonest bug class there is.
        ruling = decide(situation(
            BUILT=bool(greens),
            AMB=amb,
            CAPPED=capped,
            REFUTED=bool(res.acts_tried) and not greens,
            UNREAD=not res.acts_tried and not greens and not capped))
        res.greens = [g[0] for g in greens]
        res.capped, res.ruling = capped, ruling
        if ruling == "SHIP" and not greens:
            # unreachable by construction: BUILT is the only bit that can make
            # the law say SHIP, and BUILT is bool(greens). If this ever fires,
            # a bit was mismeasured — refuse rather than pretend.
            res.reason = ("internal: the law ruled SHIP with no candidate in "
                          "hand, which means an observation bit was measured "
                          "wrongly. Refusing rather than guessing.")
            return res
        if ruling == "SHIP":
            crepr, content, old_repr, at = greens[0]
            _write(path, content)
            res.repaired, res.refused = True, False
            res.lineno, res.old_line, res.new_line = at, old_repr, crepr
            res.restored_original = _restored_original(
                oracle.root, defect_file, at, crepr)
            res.reason = (f"engine law: BUILT -> {ruling}" if res.amb_measured
                          else f"engine law: BUILT -> {ruling} (uniqueness NOT "
                               f"measured here: the differential probe does not "
                               f"read this language, so a second passing program "
                               f"at this line would not have been seen)")
            return res
        if ruling == "ADD_STATE":
            res.ambiguous = True
            res.pinning_test = amb_rec.get("test_text") or ""
            if amb_rec.get("conservative"):
                res.reason = (
                    f"AMBIGUOUS: {len(greens)} candidates pass this suite and "
                    f"nothing here can tell whether they are the same program "
                    f"({amb_rec.get('failed') or amb_rec.get('reason') or 'no probe'}). "
                    f"Two answers this cannot separate is not a repair. Add one "
                    f"pinning test (engine law: BUILT+AMB -> {ruling}, never guess)")
            elif amb_rec.get("witness_call"):
                vals = amb_rec.get("witness_values") or []
                res.reason = (
                    f"AMBIGUOUS: {len(greens)} candidates pass this suite and "
                    f"they are DIFFERENT PROGRAMS — {amb_rec['witness_call']} "
                    f"returns {' vs '.join(map(repr, vals))}. Your tests cannot "
                    f"tell them apart, so one may CANCEL the fault rather than "
                    f"repair it. A pinning test is written out beside the "
                    f"refusal (engine law: BUILT+AMB -> {ruling}, never guess)")
            else:
                res.reason = (
                    f"AMBIGUOUS: {len(greens)} candidates at "
                    f"{len(sites)} line(s) ({', '.join(map(str, sorted(sites)))}) "
                    f"all pass the suite — the tests cannot tell them apart. Add "
                    f"one pinning test "
                    f"(engine law: BUILT+AMB -> {ruling}, never guess)")
        elif ruling == "RAISE_BUDGET" and greens:
            res.reason = (
                f"a candidate passes, but the search was cut short before it "
                f"could be shown unique — shipping it would be a guess. Raise "
                f"the budget and re-run (engine law: BUILT+CAPPED -> {ruling})")
        elif ruling == "RAISE_BUDGET":
            res.reason = (
                f"the search was cut short before the vocabulary was exhausted, "
                f"so nothing here is settled — what it did not try is unknown. "
                f"Raise the budget and re-run (engine law: CAPPED -> {ruling})")
        elif ruling == "HARVEST_COUNTEREXAMPLE":
            res.reason = (
                f"every candidate this vocabulary generated left the suite red "
                f"— the fault is outside it, or the observations are wrong. The "
                f"refusal report lists each rejection with the test that killed "
                f"it (engine law: REFUTED -> {ruling})")
        elif ruling == "ADD_MATERIAL":
            res.reason = (
                f"no observation named a kind this vocabulary can repair, so "
                f"nothing was ever generated to judge — teach the class once "
                f"(docs/TEACHING.md) or widen the search "
                f"(engine law: UNREAD -> {ruling})")
        else:
            res.reason = f"engine law: {ruling}"
        return res

    begin_inflight(oracle.root, defect_file, src)
    # THE LAW DECIDES, THIS CODE ONLY MEASURES. AMB — "one input carries two
    # outputs" — cannot be observed from a single candidate set, so greens are
    # collected across the WHOLE search and the law is asked once, at the end,
    # with the complete situation. Shipping the first green asked the law a
    # question it could not answer honestly: BUILT was true, but whether AMB
    # was also true had not been established yet.
    #
    # Measured 2026-09-04 on Unity-shaped gameplay logic: a sign flip in
    # ProjectOnPlane admitted TWO passing repairs — the real fix, and breaking
    # Vec3's operator+ so the two bugs cancel. The search found the
    # compensating one first, shipped it, and never looked at the real defect.
    # Both are green, so AMB held and the law's ruling was ADD_STATE: refuse
    # and ask for one pinning test. The ruling was right and available; the
    # situation was measured too early.
    #
    # This is the same principle the candidate-set loop already applied ("a
    # lone green with the set unfinished is an UNPROVEN-unique repair"),
    # extended to where it also holds: across observations.
    greens: list[tuple[str, str, str, int]] = []
    amb_proven = False
    set_amb = False        # two greens inside ONE candidate set
    try:
        for obs in observations:
            if deadline is not None and time.time() > deadline:
                # tree is byte-identical to src here (every candidate is
                # rolled back before the next observation) — an honest stop
                return _rule(capped=True)
            i = obs.lineno - 1
            if not (0 <= i < len(raw)):
                continue
            body = raw[i].rstrip("\r")
            ending = raw[i][len(body):]          # "" or "\r"
            mask = mask_of(k for k in obs.kinds if 0 <= k <= 15)
            while not HALT(mask):
                if deadline is not None and time.time() > deadline:
                    # between kinds the tree is byte-identical to src.
                    # NEVER inside a candidate set: a lone green with the
                    # set unfinished is an UNPROVEN-unique repair — shipping
                    # it would be a guess (adversarial review, 2026-08-31).
                    # Overshoot is bounded: one candidate set, <= 32 runs.
                    return _rule(capped=True)
                kind = kind_of(EMIT(mask))
                mask = ADVANCE(mask)
                act = act_for(kind)
                obs.file, obs.root = defect_file, oracle.root
                obs.all_lines = [l.rstrip("\r") for l in raw]
                counted = False
                # (greens accumulate across the whole search — see above)
                green_at_set_start = len(greens)
                for cand in candidates(body, act, obs):
                    if isinstance(cand, SpanEdit):
                        # the engine law's CHANGE_GRANULARITY act, actuated:
                        # one candidate replaces lines start..end atomically.
                        # Bounds AND anchor safety — a span may only edit
                        # code its own observation points into.
                        s_, e_ = cand.start, cand.end
                        if not (1 <= s_ <= e_ <= len(raw)) \
                                or not (s_ <= obs.lineno <= e_):
                            continue
                        old_repr = "\n".join(l.rstrip("\r")
                                             for l in raw[s_ - 1:e_])
                        if cand.text == old_repr:            # NOPROGRESS
                            continue
                        key = (s_, e_, cand.text)
                        cend = raw[e_ - 1][len(raw[e_ - 1].rstrip("\r")):]
                        new = raw[:s_ - 1] + [cand.text + cend] + raw[e_:]
                        crepr, at = cand.text, s_
                        at_str = f"{defect_file}:{s_}-{e_}"
                    else:
                        if cand == body:                     # NOPROGRESS
                            continue
                        key = (i, cand)
                        new = raw[:]
                        new[i] = cand + ending
                        crepr, old_repr, at = cand, body, obs.lineno
                        at_str = f"{defect_file}:{obs.lineno}"
                    if key in tried:
                        continue
                    tried.add(key)
                    if not counted:
                        res.acts_tried.append(act)           # a real candidate set
                        counted = True
                    content = "\n".join(new)
                    # a candidate that cannot even compile is rejected for
                    # free: never written, no suite run paid (.py only —
                    # jguard's Java candidates are the JVM's to judge)
                    if defect_file.endswith(".py"):
                        try:
                            compile(content, path, "exec")
                        except SyntaxError as e:
                            if len(res.tried_log) < 64:
                                res.tried_log.append(
                                    {"at": at_str, "tried": crepr[:200],
                                     "why": f"does not compile: {e}"[:400]})
                            else:
                                res.tried_more += 1
                            continue
                    _write(path, content)
                    wrote = True
                    res.suite_runs += 1
                    ok, why = oracle.check(timeout=cand_t)
                    if ok and _confirm_runs():
                        # HIDDEN, ACTUATED. A green from ONE run is a COARSE
                        # record. Re-checking produces FINE records, and when
                        # those disagree with the coarse one the situation is
                        # exactly the engine law's HIDDEN — "fine records
                        # disagree, coarse records agree" — whose ruling is
                        # CHANGE_GRANULARITY: stop judging at the granularity
                        # of a single run.
                        #
                        # This is the first of the three lanes fluidfix never
                        # measured (NOTWIN, HIDDEN, SELF) to turn out to
                        # matter. Measured 2026-09-04 against a test that
                        # skips its assert half the time: judging on one run
                        # accepted `return b - a` for `return a + b` in
                        # 7 of 50 searches (14%); consulting the law drops it
                        # to 0 of 49, and finds MORE correct repairs (10 vs
                        # 7), because a candidate that was only ever green by
                        # luck stops counting as green.
                        #
                        # The law was never wrong here. BUILT means "passed
                        # its own check" and SHIP is the right act for it —
                        # the defect was setting BUILT from a measurement
                        # that did not hold still.
                        fine_disagree = False
                        for _ in range(_confirm_runs()):
                            ok2, why2 = oracle.check(timeout=cand_t)
                            if not ok2:
                                fine_disagree, why = True, why2
                                break
                        if fine_disagree:
                            # NOTE: not recorded in acts_tried — that list
                            # holds act CODES and the refusal message branches
                            # on whether it is empty. The ruling reaches the
                            # user through `why`, which the harvest logs.
                            ruling = decide(situation(HIDDEN=True))
                            ok = False
                            why = (f"green on one run, RED on re-check — the "
                                   f"suite does not hold still here, so a "
                                   f"single run cannot judge this candidate "
                                   f"(engine law: HIDDEN -> {ruling}). "
                                   f"last failure: {why2}")
                    if ok:
                        greens.append((crepr, content, old_repr, at))
                        if len(greens) - green_at_set_start > 1:
                            # Two greens inside ONE candidate set: the suite
                            # cannot tell two DIFFERENT programs apart. This
                            # is the original AMB and it is proven here.
                            set_amb = True
                            _write(path, "\n".join(raw))
                            break
                    elif len(res.tried_log) < 64:
                        res.tried_log.append({"at": at_str,
                                              "tried": crepr[:200],
                                              "why": why})
                    else:
                        res.tried_more += 1
                    _write(path, "\n".join(raw))             # roll back, keep testing
                _write(path, src)                        # byte-exact restore
                if set_amb or len({g[3] for g in greens}) > 1:
                    amb_proven = True            # the law has enough
                    break
            if amb_proven:
                break

        # ------------------------------------------------ THE LAW RULES ----
        # Nothing above this point decides anything. The search measured the
        # situation; the law is now asked once, with all of it.
        return _rule(capped=False)
    finally:
        if wrote and not res.repaired:
            _write(path, src)
            oracle.clear_pyc()
        # The file is now either its original bytes or an ACCEPTED repair —
        # both intentional, neither something a later run should undo.
        end_inflight(oracle.root)
        res.seconds = time.time() - t0
