# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 devkancheti4-design
# Commercial licensing: see COMMERCIAL.md.
"""C/C++ support: a compile-and-run oracle behind the SAME contract surface
the repair loop already speaks — so repair(), SpanEdit, AMB refusal,
deadlines and the per-candidate failure harvest are REUSED, not
reimplemented. The kernels route integers and edit lines of text; they never
knew what Python was, they don't need to know what C is.

    green  -> build succeeds AND the test binary exits 0
    red    -> the test binary exits non-zero; failing test names and the
              assert frames (file + line) are parsed from its output
    check  -> rebuild, then run. See THE COMPILER IS A SECOND ORACLE below.

THE COMPILER IS A SECOND ORACLE. This is the one thing C changes, and it
changes it in fluidfix's favour. In Python a nonsense candidate still runs
and must be rejected by a full suite run; in C most nonsense candidates do
not compile, and the compiler says so in milliseconds without running a
single test. A candidate that fails to BUILD is therefore rejected exactly
like a candidate that fails a test — it is the candidate's fault, not the
harness's — and it is rejected roughly an order of magnitude cheaper.

The distinction that matters: the build failing on the PRISTINE tree is a
harness error (your project does not compile; there is nothing to judge
with), while the build failing on a MUTATED tree is simply a rejection.
Conflating the two would let a broken toolchain read as "every candidate is
wrong", which is the C form of the mistake the pytest oracle makes when it
treats a missing pytest as a red suite.

COST. Measured on cglm (1,131 tests, 2026-09-03, M-series):

    incremental rebuild, one .c file    ~0.50 s
    rebuild after touching a header     ~3.86 s
    test binary, all 1,131 tests         0.29 s

So a candidate costs ~0.8 s in a .c file and ~4.1 s in a header — the same
order as click's 5.7 s Python suite. The timing model is unchanged, it just
reads `build + test` where Python read `test`:

    repair time ~= suite runs x (build time + test time)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time

from .guard import _is_test_path
from .localize import Packet, _compress_failure

__all__ = ["COracle", "CBuildError", "find_candidate_files_c",
           "build_packet_c", "cguard_once"]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# `assert fail in /path/to/test_ray.h on line 68 :  ASSERT(...)`  (cglm/µunit)
# and the common `file.c:123: assertion failed` shape used by greatest/Unity.
_FRAME = re.compile(
    r"(?:assert fail in\s+(?P<f1>[^\s:]+)\s+on line\s+(?P<l1>\d+)"
    r"|(?P<f2>[\w./+-]+\.(?:c|h|cc|cpp|hpp|cxx)):(?P<l2>\d+):)")
# A failing test entry. C has no pytest monoculture: every runner prints its
# own shape, so this is a union of the ones met in the wild, widened as new
# projects are guarded. Measured 2026-09-03 — cglm marks failures with a
# cross mark and cites `assert fail in <file> on line <n>`; Box2D prints
# `test failed: MathTest` and `condition false: <expr>` with NO file or line
# anywhere. A parser tuned to one sees literally nothing in the other.
_FAILTEST = re.compile(
    r"(?:[𐄂✖✗×]\s+(?P<n1>\S+)"
    r"|(?:test|subtest)\s+failed:\s*(?P<n2>\S+)"
    r"|(?:FAILED|FAIL)[:\s]+(?P<n3>[\w:./]+)"
    r"|(?P<n4>\w+)\s+\.\.\.\s*FAILED)")


def _fail_names(clean: str) -> list[str]:
    """Every failing test name any known runner shape reports."""
    out: list[str] = []
    for m in _FAILTEST.finditer(clean):
        name = m.group("n1") or m.group("n2") or m.group("n3") or m.group("n4")
        if name and name not in out:
            out.append(name)
    return out
_SRC_EXT = (".c", ".h", ".cc", ".cpp", ".hpp", ".cxx", ".hh")


class CBuildError(RuntimeError):
    """The PRISTINE tree does not build: no verdict is possible. Distinct
    from a mutated tree failing to build, which is an ordinary rejection."""


class COracle:
    """Duck-typed to what loop.repair() needs: root, timeout, green(),
    check(), clear_pyc(). failing_output() mirrors the pytest oracle."""

    def __init__(self, root: str, build_cmd: str | None = None,
                 test_cmd: str | None = None, build_dir: str = "build",
                 timeout: int = 600, jobs: int = 8):
        self.root = os.path.abspath(root)
        self.build_dir = build_dir
        self.timeout = timeout
        self.build_cmd = build_cmd or f"cmake --build {build_dir} -j{jobs}"
        self.test_cmd = test_cmd or self._guess_test_cmd()
        self._fail_tests: list[str] = []
        self._pristine_checked = False
        self._cov = None                 # built lazily; see _Coverage

    def coverage(self):
        """The gcov tier, or None when unavailable. Built once, lazily —
        the instrumented tree is separate from the fast build so the
        candidate loop never pays for instrumentation."""
        if self._cov is None:
            self._cov = _Coverage(self)
        return self._cov

    # ---------------------------------------------------------------- guess
    def _guess_test_cmd(self) -> str:
        """A test binary the build produced, else ctest. Deliberately dumb:
        an explicit --test-cmd always wins, and the guess is reported."""
        bd = os.path.join(self.root, self.build_dir)
        for name in ("tests", "test", "unit_tests", "run_tests", "check"):
            p = os.path.join(bd, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return f"./{self.build_dir}/{name}"
        return f"ctest --test-dir {self.build_dir} --output-on-failure"

    # ------------------------------------------------------------- running
    def _sh(self, cmd: str, timeout: int | None) -> tuple[int, str]:
        try:
            p = subprocess.run(cmd, cwd=self.root, shell=True,
                               capture_output=True, text=True,
                               errors="replace",
                               timeout=timeout or self.timeout)
            return p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return 1, "TIMEOUT"

    def build(self, timeout: int | None = None) -> tuple[int, str]:
        return self._sh(self.build_cmd, timeout)

    def run(self, extra: list[str] | None = None,
            timeout: int | None = None) -> tuple[int, str]:
        """Build, then test. A build failure short-circuits with its own
        output — the caller decides whether that is a rejection or a
        harness error, because only the caller knows if the tree is
        pristine."""
        rc, out = self.build(timeout)
        if rc != 0:
            return rc, "BUILD FAILED\n" + out
        cmd = self.test_cmd + (" " + " ".join(extra) if extra else "")
        return self._sh(cmd, timeout)

    # ------------------------------------------------------------ contract
    def green(self, timeout: int | None = None) -> bool:
        rc, out = self.run(timeout=timeout)
        if rc != 0 and out.startswith("BUILD FAILED") and not self._pristine_checked:
            raise CBuildError(
                f"the project does not build in {self.root}, so no test has "
                f"been judged.\n  build command: {self.build_cmd}\n"
                f"  fix: configure the build first (e.g. cmake -S . -B "
                f"{self.build_dir}), or pass --build-cmd\n"
                f"--- last output ---\n{out.strip()[-600:]}")
        self._pristine_checked = True
        return rc == 0

    def failing_output(self) -> tuple[bool, str]:
        rc, out = self.run()
        if rc == 0:
            # same cross-examination: a suite that prints failures while
            # exiting 0 is red, and the guard should act on it
            named = _fail_names(_ANSI.sub("", out))
            if named:
                self._fail_tests = named[:40]
                return True, _ANSI.sub("", out)
            self._fail_tests = []
            return False, out
        if out.startswith("BUILD FAILED") and not self._pristine_checked:
            raise CBuildError(
                f"the project does not build in {self.root}, so no test has "
                f"been judged.\n  build command: {self.build_cmd}\n"
                f"--- last output ---\n{out.strip()[-600:]}")
        self._pristine_checked = True
        clean = _ANSI.sub("", out)
        self._fail_tests = _fail_names(clean)[:40]
        return True, clean

    def check(self, timeout: int | None = None) -> tuple[bool, str]:
        """Candidate adjudication with WHY. The build is the cheap gate: a
        candidate that will not compile is rejected without running a test.

        A GREEN EXIT CODE IS NOT ENOUGH. Measured 2026-09-04: given a test
        runner it was allowed to edit, the guard changed the harness's
        failing `return 1` to `return 0` and declared victory. The defect was
        untouched and the output still read `test failed: AddTest` — the exit
        code was the only thing that changed. Any repair tool that can reach
        its own oracle will find that edit, because it is the cheapest path
        to green. Excluding harness files by name is the first defence and it
        is not sufficient: a project may name its runner anything. So the
        output is cross-examined against the exit code, and a suite that
        still SAYS it failed is not green no matter what it returns."""
        rc, out = self.run(timeout=timeout)
        if rc == 0:
            liars = _fail_names(_ANSI.sub("", out))
            if liars:
                return False, (
                    f"suite exited 0 but still reports {len(liars)} failing "
                    f"test(s) ({', '.join(liars[:3])}) — refusing to accept a "
                    f"candidate that silences the oracle instead of repairing "
                    f"the fault")
            return True, ""
        clean = _ANSI.sub("", out)
        if clean.startswith("BUILD FAILED"):
            why = next((l.strip() for l in clean.splitlines()
                        if "error:" in l), "candidate does not compile")
            return False, why[:200]
        bad = _fail_names(clean)
        if bad:
            return False, f"{len(bad)} test(s) failed, first: {bad[0]}"
        why = next((l.strip() for l in clean.splitlines()
                    if "fail" in l.lower()), "suite red")
        return False, why[:200]

    def clear_pyc(self) -> None:            # the build system tracks its own
        pass


# ------------------------------------------------------------- coverage --
# THE GCOV TIER. What C was missing, and it was the whole gap.
#
# Python's guard ranks files by SPECIFICITY: of the lines a file executes,
# what fraction come from the FAILING tests rather than the whole suite. That
# single measurement drives the SIGHT law's FAILONLY lane (implicated) and
# its UBIQUITOUS penalty (every test touches it). Without it the C adapter
# had no evidence at all when the failing test's NAME pointed nowhere.
#
# Measured on Box2D 2026-09-04: a pointer-arithmetic defect in
# src/contact_solver.c whose failing tests are `MultithreadingTest` and
# `DeterminismTest` — names that match no source file. With no frames, no
# literal and no name affinity, ranking fell back to file size, the defect
# file landed 3rd, and 192 candidates over an hour did not reach it.
#
# gcov supplies exactly the missing lane, and cheaply: a separate
# instrumented build directory, kept beside the fast one so the normal
# candidate loop never pays for instrumentation.

_GCOV_LINE = re.compile(r"^\s*([^:]+):\s*(\d+):")


class _Coverage:
    """Executed-line sets per source file, from a gcov-instrumented build."""

    def __init__(self, oracle: "COracle", cov_dir: str = "covbuild"):
        self.o = oracle
        self.cov_dir = cov_dir
        self._ready = False

    def available(self) -> bool:
        return shutil.which("gcov") is not None

    def _ensure_build(self, timeout: int | None = None) -> bool:
        """Configure and build the instrumented tree once. Returns False (no
        coverage tier, not an error) if the project will not build with
        --coverage — plenty of projects will not, and the guard must degrade
        to the evidence it does have rather than refuse outright."""
        if self._ready:
            return True
        if not self.available():
            return False
        path = os.path.join(self.o.root, self.cov_dir)
        if not os.path.isdir(path):
            rc, _ = self.o._sh(
                f'cmake -S . -B {self.cov_dir} -DCMAKE_BUILD_TYPE=Debug '
                f'-DCMAKE_C_FLAGS="--coverage -O0" '
                f'-DCMAKE_CXX_FLAGS="--coverage -O0" '
                f'-DCMAKE_EXE_LINKER_FLAGS="--coverage"', timeout)
            if rc != 0:
                return False
        rc, _ = self.o._sh(f"cmake --build {self.cov_dir} -j8", timeout)
        self._ready = rc == 0
        return self._ready

    def _test_binary(self) -> str | None:
        bd = os.path.join(self.o.root, self.cov_dir)
        for sub in ("bin", "", "test"):
            for name in ("tests", "test", "unit_tests", "run_tests"):
                p = os.path.join(bd, sub, name)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    return os.path.relpath(p, self.o.root)
        return None

    def lines(self, test_filter: str | None = None,
              timeout: int | None = None) -> dict[str, set[int]]:
        """rel-path -> set of executed line numbers. Empty dict when the
        tier is unavailable; the caller then falls back to what it had."""
        if not self._ensure_build(timeout):
            return {}
        binary = self._test_binary()
        if binary is None:
            return {}
        for dp, _dn, fns in os.walk(os.path.join(self.o.root, self.cov_dir)):
            for fn in fns:
                if fn.endswith(".gcda"):
                    try:
                        os.remove(os.path.join(dp, fn))
                    except OSError:
                        pass
        self.o._sh(f"./{binary}" + (f" {test_filter}" if test_filter else ""),
                   timeout)
        out: dict[str, set[int]] = {}
        for dp, _dn, fns in os.walk(os.path.join(self.o.root, self.cov_dir)):
            gcda = [f for f in fns if f.endswith(".gcda")]
            if not gcda:
                continue
            self.o._sh(
                f'cd "{dp}" && gcov ' + " ".join(f'"{g}"' for g in gcda), timeout)
            for fn in os.listdir(dp):
                if not fn.endswith(".gcov"):
                    continue
                full = os.path.join(dp, fn)
                try:
                    src_rel, hit = None, set()
                    with open(full, encoding="utf-8", errors="replace") as fh:
                        for line in fh:
                            if line.startswith("        -:    0:Source:"):
                                src = line.split("Source:", 1)[1].strip()
                                src = os.path.normpath(src)
                                if src.startswith(self.o.root + os.sep):
                                    src_rel = os.path.relpath(
                                        src, self.o.root).replace("\\", "/")
                                continue
                            m = _GCOV_LINE.match(line)
                            if not m:
                                continue
                            cnt = m.group(1).strip()
                            if cnt and cnt[0].isdigit() and cnt != "0":
                                hit.add(int(m.group(2)))
                    if src_rel and hit and not _is_test_path(src_rel):
                        out.setdefault(src_rel, set()).update(hit)
                finally:
                    try:
                        os.remove(full)
                    except OSError:
                        pass
        return out


# ------------------------------------------------------------ localisation
# THE ORACLE IS NOT A CANDIDATE. If the guard can edit the tests, it can
# "repair" anything by weakening the assertion that caught the regression —
# the one failure mode that would make every other guarantee worthless.
# Python has `test_*.py` and `tests/` to lean on; C names its harness
# whatever it likes. Caught 2026-09-04 by the adapter's own end-to-end test:
# a runner at the repo root was not recognised as test code, and the guard
# repaired the RUNNER rather than the defect. Directory exclusion is the
# main defence; this catches the common root-level harness names.
_HARNESS = re.compile(
    r"^(?:test[_-]?.*|.*[_-]tests?|runner|test_runner|unit_?tests?|"
    r"catch_?main|gtest_main|doctest_main)\.(?:c|h|cc|cpp|hpp|cxx|hh)$",
    re.I)


def _is_harness_file(basename: str) -> bool:
    return bool(_HARNESS.match(basename))


def _c_sources(root: str, build_dir: str = "build") -> dict[str, str]:
    """basename -> repo-relative path, PRODUCTION sources only."""
    out: dict[str, str] = {}
    # Measured on Box2D 2026-09-03: `DeterminismTest` matched
    # `shared/determinism.c` and `samples/sample_determinism.cpp` — demo and
    # harness code that cannot hold a library defect — while the real fault
    # sat in src/contact_solver.c. Sample/benchmark trees are never the
    # thing under test.
    skip = {".git", build_dir, "node_modules", "third_party", "external",
            "vendor", "deps", "subprojects", "cmake-build-debug",
            "samples", "sample", "benchmark", "benchmarks", "examples",
            "extern", "docs", "shared"}
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in skip and not d.startswith(".")]
        rel_dp = os.path.relpath(dp, root).replace("\\", "/")
        if re.search(r"(^|/)(tests?|testing)(/|$)", rel_dp):
            continue
        for fn in fns:
            if fn.endswith(_SRC_EXT) and not _is_harness_file(fn):
                out.setdefault(fn, f"{rel_dp}/{fn}".lstrip("./"))
    return out


def find_candidate_files_c(oracle: COracle, failing_output: str,
                           limit: int = 5) -> list[str]:
    """Assert frames first, but in C those usually name the TEST file — the
    assertion fires in the test, not in the code under test. So the real
    work is the NAMED convention: a failing test called `glm_vec3_add` shares
    the token `vec3` with `vec3.h`. Same lane the SIGHT law reads, resolved
    here against the project's own source basenames."""
    srcs = _c_sources(oracle.root, oracle.build_dir)
    clean = _ANSI.sub("", failing_output)
    ordered: list[str] = []

    for m in _FRAME.finditer(clean):
        base = os.path.basename(m.group("f1") or m.group("f2") or "")
        rel = srcs.get(base)
        if rel and rel not in ordered:
            ordered.append(rel)

    # Token affinity from the failing test names. Two things this must get
    # right, both learned the hard way on cglm (2026-09-03):
    #
    #  * a stem maps to a LIST, not one file. `vec3.c` and `vec3.h` share the
    #    stem `vec3`, and in a header-implemented library the .c is a
    #    five-line wrapper while the header holds every line that can carry a
    #    defect. Keeping only one silently searched the wrapper.
    #  * do NOT split between a letter and a digit. `vec3` is the token that
    #    identifies the module; splitting it into `vec` + `3` throws away the
    #    only discriminating evidence in the test's name.
    stems: dict[str, list[str]] = {}
    for b, r in srcs.items():
        stems.setdefault(os.path.splitext(b)[0].lower(), []).append(r)
    scored: dict[str, int] = {}
    for name in oracle._fail_tests or _fail_names(clean):
        # Split separators AND camel humps: `MathTest` is one token to a
        # naive splitter, and `math` is the only part that names anything.
        parts = re.split(r"[^A-Za-z0-9]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])",
                                                  "_", name))
        toks = [t for t in (p.lower() for p in parts) if len(t) >= 3]
        for t in toks:
            if t in ("test", "tests"):
                continue
            for rel in stems.get(t, ()):          # exact stem: strong
                if rel not in ordered:
                    scored[rel] = scored.get(rel, 0) + 3
            for stem, rels in stems.items():      # partial: `math` in
                if stem != t and (t in stem.split("_")   # `math_functions`
                                  or stem.startswith(t + "_")):
                    for rel in rels:
                        if rel not in ordered:
                            scored[rel] = scored.get(rel, 0) + 1
    # More failing tests naming a file is stronger evidence; ties go to the
    # bigger file, which in a header-implemented project is the one holding
    # the implementation rather than the wrapper.
    def _size(rel):
        try:
            return os.path.getsize(os.path.join(oracle.root, rel))
        except OSError:
            return 0
    ordered += [r for r, _ in sorted(scored.items(),
                                     key=lambda kv: (-kv[1], -_size(kv[0]),
                                                     kv[0]))]
    if not ordered:
        # NOTHING POINTED ANYWHERE. C offers no traceback frame here and no
        # coverage tier, so there is no evidence to rank on — the SIGHT
        # law's evidence-gap case, in its purest form. Searching every
        # source is honest but, at a compile per candidate, rarely
        # economical; the caller reports that rather than pretending the
        # order means something.
        ordered = sorted(srcs.values(), key=lambda r: (-_size(r), r))
    return ordered[:limit]


def build_packet_c(oracle: COracle, defect_file: str, failing_output: str,
                   max_lines: int = 110,
                   covered: set | None = None) -> Packet | None:
    """Frames in this file (+/-12 lines) when one names it; else every code
    line, signal-filtered and spread-sampled — same Packet type, same
    truncation semantics the engine law's CAPPED ruling reads."""
    path = os.path.join(oracle.root, defect_file)
    try:
        src = open(path, encoding="utf-8", newline="").read()
    except OSError:
        return None
    src_lines = src.split("\n")
    base = os.path.basename(defect_file)
    clean = _ANSI.sub("", failing_output)

    frames: set[int] = set()
    for m in _FRAME.finditer(clean):
        f = os.path.basename(m.group("f1") or m.group("f2") or "")
        if f == base:
            ln = int(m.group("l1") or m.group("l2"))
            frames.update(range(max(1, ln - 12),
                                min(len(src_lines), ln + 12) + 1))
    # COVERAGE FIRST. The lines the failing test actually executed beat any
    # guess about which lines could matter — this is the tier Python has had
    # from the start via pytest-cov. Measured on Box2D 2026-09-04: the
    # failing test executes 608 of contact_solver.c's ~2,100 lines, and the
    # defect (line 2032) is among them; without this the anchor set was
    # guessed and the defect could be sampled away entirely.
    executed = covered or set()
    lo = sorted(frames) if frames else sorted(
        l for l in (executed or set())
        if 1 <= l <= len(src_lines) and src_lines[l - 1].strip())
    mode = "frames" if frames else ("coverage" if lo else "affinity")
    if not lo:
        lo = [i + 1 for i, l in enumerate(src_lines)
              if l.strip() and not l.lstrip().startswith(
                  ("//", "*", "/*", "#include", "#ifndef", "#define",
                   "#endif", "#ifdef"))]
    filtered = False

    # THE TAUGHT CLASS IS A LINE FILTER, NOT ONLY A MATCHER.
    #
    # Python gets its anchor lines from pytest-cov: it KNOWS which lines the
    # failing tests executed. C has no such tier here, so an over-long file
    # used to be spread-sampled down to max_lines — and sampling is blind.
    # Measured on cglm 2026-09-03: vec3.h reduced 583 code lines -> 361 ->
    # 110 anchors, and the stride stepped straight over the defect. It kept
    # lines 283 and 286 and dropped 284, the broken line. The guard searched
    # the right file for ~15 minutes and could never have found the fault.
    #
    # A registered class's signal answers "can this line exhibit the class?".
    # Keeping the lines that match ANY taught signal is therefore a filter
    # that cannot drop a line the vocabulary could repair — and it shrinks
    # the search to the lines worth compiling for, which in C is the whole
    # cost. Same insight as the SIGHT law's SCARCE lane, applied to lines.
    if len(lo) > max_lines:
        try:
            from .acts import KINDS
            sigs = [e[2] for e in KINDS.values() if e[2] is not None]
            keep = [l for l in lo
                    if any(g.search(src_lines[l - 1]) for g in sigs)]
            if keep:
                filtered = len(keep) < len(lo)
                lo = keep
            # Still over budget? Then RANK by signal rarity rather than
            # sampling blindly. A signal matching 5 lines in this file says
            # far more than one matching 300 — the SIGHT law's SCARCE lane,
            # one level down. Measured on Box2D 2026-09-03: 388 of 616 lines
            # in math_functions.h match some taught signal (`\d` alone
            # matches any line with a digit), so the vocabulary filter on its
            # own does not fit the budget and the stride dropped the defect.
            if len(lo) > max_lines:
                hits = {}
                for g in sigs:
                    n = sum(1 for l in lo if g.search(src_lines[l - 1]))
                    if n:
                        hits[g] = n
                def _rarity(l):
                    ns = [n for g, n in hits.items()
                          if g.search(src_lines[l - 1])]
                    return min(ns) if ns else 10 ** 6
                lo = sorted(sorted(lo), key=_rarity)[:max_lines]
                lo.sort()
                filtered = True
        except Exception:                                   # noqa: BLE001
            pass

    if len(lo) > max_lines - 30:
        sig = re.compile(r"[<>]=?|\d|\s[-+*/]\s|&&|\|\||\[|return")
        kept = [l for l in lo if sig.search(src_lines[l - 1])] or lo
        filtered = filtered or len(kept) < len(lo)
        lo = kept
    truncated = len(lo) > max_lines or filtered
    if len(lo) > max_lines:
        # Still too many even after the vocabulary filter: sample, but say so
        # — `truncated` is what the engine law reads as CAPPED, and a capped
        # packet is why RAISE_BUDGET exists.
        stride = len(lo) / max_lines
        lo = [lo[int(i * stride)] for i in range(max_lines)]
    return Packet(defect_file=defect_file,
                  failure=_compress_failure(clean),
                  lines=lo, src_lines=src_lines,
                  mode=mode,
                  truncated=truncated)


def cguard_once(oracle: COracle, observer, candidate_timeout=None,
                budget: int | None = None):
    """One C guard pass. Same shape as jguard_once, with the gcov tier
    slotted in exactly where pytest-cov sits on the Python side."""
    from .guard import GuardReport
    from .loop import repair

    t0 = time.time()
    deadline = t0 + budget if budget else None
    fails, out = oracle.failing_output()
    if not fails:
        return GuardReport(status="green", seconds=time.time() - t0)
    candidates = find_candidate_files_c(oracle, out)

    # THE GCOV TIER, if the project supports it. Two measurements, both
    # cheap (0.5s and 0.3s on Box2D): the lines the FAILING test executes,
    # and the lines the whole suite executes. Specificity ranks files; the
    # per-file executed set anchors the packet.
    fail_cov: dict = {}
    try:
        cov = oracle.coverage()
        if cov.available():
            # UNION ACROSS EVERY FAILING TEST, not just the first.
            # Measured on Box2D 2026-09-04: the first reported failure,
            # `MultithreadingTest`, PASSES in isolation and executes 38 lines
            # of the harness and nothing else. Probing it alone produced
            # coverage of two files, neither of them the defect's — and the
            # "drop what the failure never executed" rule below then threw
            # the real defect file away. A test that only fails in
            # combination covers nothing on its own.
            fail_cov = {}
            for probe in (oracle._fail_tests or [None])[:4]:
                for rel, hit in cov.lines(probe).items():
                    fail_cov.setdefault(rel, set()).update(hit)
            full_cov = cov.lines() if fail_cov else {}
            real = [r for r in fail_cov if not _is_test_path(r)]
            if len(real) < 5:
                # Degenerate probe: the filtered runs told us almost nothing.
                # Fall back to whole-suite coverage, which at least says
                # which lines exist at runtime, and never drop on this.
                fail_cov = {r: h for r, h in full_cov.items()}
                credible = False
            else:
                credible = True
            if fail_cov:
                def _spec(rel):
                    f = len(fail_cov.get(rel, ()))
                    u = max(len(full_cov.get(rel, ())), f, 1)
                    return min(f / u, 1.0)      # clamp: a filtered run can
                                                # execute lines the full one
                                                # does not (different order)
                seen = set(candidates)
                extra = [r for r in fail_cov if r not in seen
                         and not _is_test_path(r)]
                # executed-by-the-failure first, most specific and cheapest
                # to search first among equals
                extra.sort(key=lambda r: (-_spec(r), len(fail_cov[r]), r))
                candidates = candidates + extra
                # Drop what the failure never executed — a line that did
                # not run cannot be the fault — but ONLY when the coverage
                # is credible. Dropping on a degenerate probe is how the
                # defect file got discarded; ordering is safe either way.
                if credible:
                    touched = [c for c in candidates if c in fail_cov]
                    if len(touched) >= 3:
                        candidates = touched
    except Exception:                                       # noqa: BLE001
        fail_cov = {}

    attempts: list = []
    for rel in candidates:
        if deadline is not None and time.time() > deadline:
            return GuardReport(status="refused", candidates=candidates,
                               seconds=time.time() - t0, attempts=attempts,
                               hint=f"--budget exhausted ({budget}s)")
        packet = build_packet_c(oracle, rel, out,
                                covered=fail_cov.get(rel))
        if packet is None:
            continue
        observations = observer.observe([packet])[0]
        result = repair(oracle, rel, observations,
                        candidate_timeout=candidate_timeout, deadline=deadline)
        attempts += result.tried_log
        if result.repaired:
            return GuardReport(status="repaired", file=rel, result=result,
                               candidates=candidates, seconds=time.time() - t0,
                               attempts=attempts)
        if result.ambiguous:
            return GuardReport(status="refused", file=rel, result=result,
                               candidates=candidates, seconds=time.time() - t0,
                               hint=result.reason, attempts=attempts)
    return GuardReport(status="refused", candidates=candidates,
                       seconds=time.time() - t0, attempts=attempts)
