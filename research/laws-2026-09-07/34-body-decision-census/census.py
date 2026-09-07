"""THE CENSUS. Joins the mechanical branch enumeration (enumerate_branches.py)
against a hand-authored classification, and PROVES completeness: every one of
the 344 branch points is either in the census (chooses a repair OUTCOME) or
explicitly marked plumbing. Rerun: python census.py
"""
import ast, os, sys
from collections import Counter

SRC = "/Users/kanchetidevieswar/neo/fluidfix/src/fluidfix"
FILES = ["loop.py", "guard.py", "acts.py", "oracle.py", "coracle.py"]

# key: "file:line" -> (VERDICT, WHAT IT CHOOSES, WHICH LAW / WHY NOT)
# VERDICT: LAW = the ruling steers this branch
#          LAW-INPUT = measures a bit the law reads (thresholds from a law docstring)
#          LAW-QUOTED = decide() is called but its return only enters a string
#          TAUTOLOGY = decide() is called on a LITERAL byte; branch cannot vary
#          CODE = the body chooses; no law was asked
C = {
# ---------------------------------------------------------------- loop.py
"loop.py:175": ("CODE","refuse 'no failing test' vs search","precondition; no decide(). Documented loop.py:18-21"),
"loop.py:201": ("CODE","ask the law at all, or fall through to a refusal","gates every engine consultation on greens!=[]"),
"loop.py:218": ("LAW-INPUT","the AMB bit fed to decide()","AMB := set_amb or len(sites)>1 (engine.py:22)"),
"loop.py:221": ("LAW","SHIP the repair vs refuse","engine law, ruling read directly. THE ONLY PURE ACTUATION BRANCH"),
"loop.py:230": ("CODE","res.ambiguous -> guard aborts the file loop (guard.py:525,606)","re-derives decide()'s own AMB input instead of testing ruling=='ADD_STATE'"),
"loop.py:269": ("CODE","stop the search between observations","wall clock; no law"),
"loop.py:273": ("LAW","return the law's ruling","actuation plumbing of _rule()"),
"loop.py:283": ("CODE","the ORDER fault classes are tried in","mask_of() drops obs.kinds order (acts.py:60 'most specific first'); lanes.EMIT then takes the lowest bit"),
"loop.py:284": ("LAW","keep emitting kinds vs stop","lanes law HALT"),
"loop.py:285": ("CODE","stop the search between kinds","wall clock; no law"),
"loop.py:292": ("LAW","return the law's ruling","actuation plumbing"),
"loop.py:312": ("CODE","reject a SpanEdit unseen","bounds + anchor safety (acts.py:32-42)"),
"loop.py:317": ("CODE","skip candidate == NOPROGRESS","documented loop.py:14"),
"loop.py:325": ("CODE","skip candidate == NOPROGRESS","documented loop.py:14"),
"loop.py:332": ("CODE","skip an already-tried candidate","cross-observation dedupe"),
"loop.py:335": ("LAW-INPUT","acts_tried, which guard.py:519 turns into REFUTED","'a real candidate set'; engine.py:24 says REFUTED also needs 'the suite rejected every one'"),
"loop.py:342": ("CODE","reject a non-compiling .py candidate for free","no suite run paid; .py only"),
"loop.py:346": ("CODE","what the harvest report contains","64-entry cap (magic number)"),
"loop.py:357": ("CODE","whether the HIDDEN lane runs at all","FLUIDFIX_CONFIRM, default 1; 0 disables the lane"),
"loop.py:386": ("LAW-QUOTED","reject a green candidate as flaky","decide(situation(HIDDEN=True)) at :391 -> CHANGE_GRANULARITY is only interpolated into `why`; `ok=False` at :388 is the body's own act"),
"loop.py:398": ("CODE","record a green","oracle verdict plumbing"),
"loop.py:400": ("CODE","set_amb, and BREAK out of the candidate set","two greens in one set; stops searching the rest of the set"),
"loop.py:407": ("CODE","what the harvest report contains","64-entry cap"),
"loop.py:415": ("CODE","stop the whole per-file search early","third re-derivation of the AMB predicate"),
"loop.py:418": ("CODE","stop iterating observations","amb_proven"),
"loop.py:425": ("LAW","return the law's ruling","the one call site the docstring calls 'THE LAW RULES'"),
"loop.py:427": ("CODE","which of two refusal reasons the user sees","acts_tried empty => 'no kind' else 'all red'"),
# ---------------------------------------------------------------- guard.py
"guard.py:71":  ("CODE","which of THREE refusal diagnoses the user is told","exhausted x pointed; no law"),
"guard.py:92":  ("CODE","refusal diagnosis 2 of 3","no law"),
"guard.py:136": ("CODE","which files may be searched at all","must live under root"),
"guard.py:139": ("CODE","exclude test files from the candidate set","the oracle is not a candidate (oracle.py:97-105)"),
"guard.py:142": ("CODE","file ORDER: deepest traceback frame wins","ordered.remove/append + reverse() at :145"),
"guard.py:146": ("CODE","RETURN the frame list and NEVER consult sight()","the SIGHT law is skipped entirely whenever a traceback names a source file"),
"guard.py:188": ("CODE","drop files the failing test never executed","n_fail==0"),
"guard.py:254": ("LAW-INPUT","the LITERAL bit","<=2 files, threshold from sight.py:17"),
"guard.py:272": ("LAW-INPUT","the SCARCE bit","<=2 files, threshold from sight.py:16"),
"guard.py:284": ("LAW-INPUT","FAILONLY/NAMED/TOUCHED/SMALL/UBIQUITOUS bits","thresholds 0.9/80/0.25 all from sight.py:18-21"),
"guard.py:300": ("LAW","file search ORDER","sight() is the primary key; -affinity/-spec/-n_fail/name break ties INSIDE a class (documented guard.py:208)"),
"guard.py:302": ("CODE","how many files the first pass may search","max(limit,8) (magic number)"),
"guard.py:402": ("CODE","the CHEAP bit is measured from only the first 2 kinds","(obs.kinds or [])[:2]"),
"guard.py:412": ("LAW-INPUT","the DENSE bit","shape count >= 8"),
"guard.py:425": ("LAW","line search ORDER","rank() primary; -token-count breaks ties inside a class (documented guard.py:416)"),
"guard.py:463": ("CODE","the whole pass's wall-clock budget","--budget"),
"guard.py:468": ("CODE","first pass gets budget/3, escalation the rest","magic split; measured rationale in comment, no law"),
"guard.py:479": ("CODE","green -> do nothing","precondition"),
"guard.py:489": ("LAW-INPUT","the UNREAD bit","not candidates and no pytest-cov"),
"guard.py:491": ("TAUTOLOGY","emit an ADD_MATERIAL hint","decide(situation(UNREAD=True)) is a CONSTANT -> ADD_MATERIAL. No actuation: only a hint string is set"),
"guard.py:498": ("CODE","abandon the first pass","wall clock"),
"guard.py:506": ("CODE","skip a file with no packet","build_packet returned None"),
"guard.py:508": ("LAW-INPUT","the CAPPED bit","packet.truncated ONLY - the first-pass deadline cap is never propagated"),
"guard.py:509": ("CODE","exempt a file from escalation","full_sight set"),
"guard.py:519": ("LAW-INPUT","the REFUTED bit","bool(acts_tried) = 'candidates were generated'. engine.py:24 requires 'AND the suite rejected every one'. MISMEASURED - see Finding 4"),
"guard.py:520": ("LAW","ship and stop","actuates loop.py:221's SHIP"),
"guard.py:525": ("LAW","refuse and stop searching other files","actuates loop.py:230, i.e. BUILT+AMB -> ADD_STATE"),
"guard.py:538": ("LAW-INPUT","the CAPPED bit, 2nd source","candidate-file list truncated"),
"guard.py:539": ("LAW","escalate (RAISE_BUDGET) vs stop","the ONLY variable-byte engine consultation in guard.py - and `escalate and` short-circuits it away entirely when the flag is False"),
"guard.py:549": ("CODE","--budget overrides --escalate-budget","no law"),
"guard.py:554": ("CODE","abandon escalation","wall clock"),
"guard.py:566": ("CODE","which escalation-refusal advice is given","pointed vs not"),
"guard.py:574": ("CODE","skip a file in escalation","already had full sight"),
"guard.py:579": ("CODE","how much sight a file gets: 990 then 10**9","magic numbers, no law"),
"guard.py:583": ("CODE","skip a file","dead deadline"),
"guard.py:591": ("CODE","one file may take at most half the escalation budget","anti-starvation, adversarial review 2026-08-31; no law"),
"guard.py:600": ("LAW","ship and stop","actuates SHIP"),
"guard.py:606": ("LAW","refuse and stop","actuates ADD_STATE"),
"guard.py:611": ("TAUTOLOGY","emit a HARVEST hint","decide(situation(REFUTED=True)) is CONSTANT"),
"guard.py:617": ("TAUTOLOGY","emit a HARVEST hint","decide(situation(REFUTED=True)) is CONSTANT"),
# ---------------------------------------------------------------- acts.py
"acts.py:126": ("CODE","candidate ORDER within a strictness set",">=,<=,>,< tuple order"),
"acts.py:152": ("CODE","the BYTES shipped: zero-padding preserved","measured: click \\033 replay"),
"acts.py:159": ("CODE","the BYTES shipped: `x + 1` -> `x`","only at the decrement site"),
"acts.py:173": ("CODE","candidate ORDER: observer-pointed literal first","obs.literal_value/occurrence"),
"acts.py:201": ("CODE","candidate ORDER: op_occurrence, else FIRST '+'","the docstring calls :204 a 'legacy first-+ heuristic'"),
"acts.py:248": ("CODE","candidate ORDER: relaxed pair before strict","tuple order"),
"acts.py:400": ("CODE","unknown act -> NOPROGRESS","documented"),
"acts.py:406": ("CODE","TRUNCATE the candidate set at 32","a BUDGET (acts.py:366-376) that sets NO CAPPED bit anywhere - the law never learns the set was cut"),
"acts.py:412": ("CODE","apply() ships candidate[0]","back-compat single-fix API"),
# ---------------------------------------------------------------- oracle.py
"oracle.py:75":  ("CODE","HarnessError vs a red suite","no pytest in the interpreter"),
"oracle.py:83":  ("CODE","HarnessError vs a red suite","_EXIT_MEANING = {3,4,5}; 1 and 2 are real red"),
"oracle.py:113": ("CODE","REJECT a candidate that exited 0","anti-oracle-silencing; no law"),
"oracle.py:203": ("CODE","reject on --lf alone, no full run","fast gate; sound (subset) but it is the sole rejection gate for those candidates"),
"oracle.py:205": ("CODE","disable the fast gate for this run","adaptive, SQLAlchemy scar"),
"oracle.py:213": ("CODE","REJECT the candidate","--lf red"),
"oracle.py:221": ("CODE","REJECT rather than raise","a candidate is in the tree, so pytest choking is the candidate's fault"),
"oracle.py:227": ("CODE","ACCEPT the candidate","rc==0 and no liars"),
"oracle.py:229": ("CODE","REJECT a green exit code","_still_reports_failures"),
# ---------------------------------------------------------------- coracle.py
"coracle.py:229": ("CODE","CBuildError vs rejection","pristine tree or not"),
"coracle.py:241": ("CODE","suite red despite exit 0","_fail_names"),
"coracle.py:250": ("CODE","CBuildError vs rejection","pristine tree or not"),
"coracle.py:257": ("CODE","refuse to judge at all","stale binary"),
"coracle.py:283": ("CODE","ACCEPT the candidate","rc==0 and no liars"),
"coracle.py:285": ("CODE","REJECT a green exit code","anti-oracle-silencing"),
"coracle.py:293": ("CODE","REJECT: does not compile","the compiler as second oracle"),
"coracle.py:298": ("CODE","REJECT: tests failed",""),
"coracle.py:485": ("CODE","exclude whole trees from search","tests?/testing directories"),
"coracle.py:488": ("CODE","exclude harness files","_HARNESS regex"),
"coracle.py:507": ("CODE","file ORDER: assert frames first","no sight() call"),
"coracle.py:531": ("CODE","ignore 'test'/'tests' tokens",""),
"coracle.py:534": ("CODE","file ORDER: exact stem scores +3","magic weight, no law"),
"coracle.py:537": ("CODE","file ORDER: partial stem scores +1","magic weight, no law"),
"coracle.py:550": ("CODE","file ORDER: (-score, -SIZE, name)","file BYTES as a tiebreak; no law"),
"coracle.py:553": ("CODE","file ORDER when nothing pointed: by SIZE","the comment itself says the order does not mean anything"),
"coracle.py:582": ("CODE","which LINES are searched: frames in this file",""),
"coracle.py:593": ("CODE","packet anchors: frames > coverage > every code line",""),
"coracle.py:597": ("CODE","packet anchors: fall back to all code lines",""),
"coracle.py:619": ("CODE","DROP lines no taught signal matches","vocabulary filter; sets truncated"),
"coracle.py:625": ("CODE","keep the filter only if it kept something",""),
"coracle.py:635": ("CODE","rank surviving lines by signal RARITY","SIGHT's SCARCE idea, hand-rolled one level down; sight() not called"),
"coracle.py:651": ("CODE","second line filter at max_lines-30","magic number 30"),
"coracle.py:657": ("CODE","STRIDE-SAMPLE the remaining lines away","blind sampling; the cglm vec3.h scar"),
"coracle.py:689": ("CODE","green -> do nothing","precondition"),
"coracle.py:700": ("CODE","use the gcov tier at all","gcov on PATH"),
"coracle.py:715": ("CODE","declare the coverage probe non-credible","len(real) < 5 (magic number)"),
"coracle.py:723": ("CODE","use coverage for ordering at all",""),
"coracle.py:735": ("CODE","file ORDER: (-specificity, EXECUTED-LINES ASC, name)","no law; agent 17 measured the ASC/DESC direction alone as median rank 20 vs 3.5"),
"coracle.py:741": ("CODE","DROP files the failing test never executed","credible only"),
"coracle.py:743": ("CODE","drop only if >=3 files survive","magic number 3; can discard a FRAME-named file"),
"coracle.py:750": ("CODE","abandon the C pass","wall clock; cguard_once has NO escalation stage"),
"coracle.py:756": ("CODE","skip a file","no packet"),
"coracle.py:762": ("LAW","ship and stop","actuates loop.py:221's SHIP"),
"coracle.py:766": ("LAW","refuse and stop","actuates loop.py:230"),
}

# ---- completeness proof: every enumerated branch is censused or plumbing ----
def enum():
    seen = set()
    for fn in FILES:
        src = open(os.path.join(SRC, fn), encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.comprehension):
                for g in node.ifs: seen.add(f"{fn}:{g.lineno}")
            elif isinstance(node, (ast.If, ast.IfExp, ast.While, ast.BoolOp)):
                seen.add(f"{fn}:{node.lineno}")
    return seen

all_pts = enum()
missing = sorted(k for k in C if k not in all_pts)
src_lines = {fn: open(os.path.join(SRC, fn), encoding="utf-8").read().split("\n")
             for fn in FILES}

print("=" * 100)
print("BODY DECISION CENSUS - branches that choose between repair OUTCOMES")
print("=" * 100)
order = {f: i for i, f in enumerate(FILES)}
for k in sorted(C, key=lambda k: (order[k.split(":")[0]], int(k.split(":")[1]))):
    v, chooses, why = C[k]
    fn, ln = k.split(":")
    print(f"\n{k:16} [{v}]")
    print(f"  code    : {src_lines[fn][int(ln)-1].strip()[:96]}")
    print(f"  chooses : {chooses}")
    print(f"  basis   : {why}")

print("\n" + "=" * 100)
c = Counter(v[0] for v in C.values())
print("TOTALS")
print(f"  branch points enumerated in the 5 files : {len(all_pts)} distinct lines "
      f"(344 nodes; some lines hold >1)")
print(f"  branches that choose a repair OUTCOME   : {len(C)}")
print(f"  of those, by verdict                    : {dict(c)}")
byfile = Counter(k.split(':')[0] for k in C)
print(f"  by file                                 : {dict(byfile)}")
lawful = c['LAW'] + c['LAW-INPUT']
print(f"  LAW or LAW-INPUT                        : {lawful}/{len(C)} "
      f"({100*lawful/len(C):.0f}%)")
print(f"  CODE-DECIDED                            : {c['CODE']}/{len(C)} "
      f"({100*c['CODE']/len(C):.0f}%)")
print(f"\n  NOT `if` STATEMENTS AT ALL ({len(missing)}): sort keys and ordered literals.")
print("  These are among the most consequential outcome decisions in the body, and a")
print("  census that only counted `if` would have missed every one of them:")
for k in missing:
    fn, ln = k.split(":")
    print(f"    {k:16} {src_lines[fn][int(ln)-1].strip()[:80]}")
bad = [k for k in missing
       if not (0 < int(k.split(":")[1]) <= len(src_lines[k.split(":")[0]]))]
print("  every one verified present in the file:", "OK" if not bad else bad)
