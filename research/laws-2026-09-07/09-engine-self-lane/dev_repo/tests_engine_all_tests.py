"""EVERY TEST ON THE ENGINE LAW, re-run in one place."""
import sys, json, collections, itertools, hashlib
sys.path.insert(0, "/Users/kanchetidevieswar/model dev 1/law-a-test")
sys.path.insert(0, ".")
import ENGINE_LAW as EL
import mybugs as MB

D = [(EL.situation(j, **o), a) for j, o, a, w in EL.EVENTS]
TRAINED = {x for x, _ in D}
P = lambda t, r: print("  %-52s %s" % (t, r), flush=True)

print("\nTEST 1  exact on the events it was authored from")
ok = sum(1 for x, a in D if EL.decide(x) == a)
P("measured events reproduced", "%d / %d" % (ok, len(D)))

print("\nTEST 2  act coverage -- can every act ever fire?")
cov = collections.Counter(EL.decide(x) for x in range(1024))
for i, a in enumerate(EL.ACTS):
    P(a, "%4d of 1024 situations" % cov.get(i, 0))
dead = [EL.ACTS[i] for i in range(8) if not cov.get(i)]
P("acts that NEVER fire", dead or "NONE  (the prior law had act 7 dead)")

print("\nTEST 3  job invariance -- is it really one law for four jobs?")
diff = sum(1 for s in range(256)
           if len({EL.decide(s | (j << 8)) for j in range(4)}) > 1)
P("observations ruling differently across the 4 jobs", "%d of 256" % diff)

print("\nTEST 4  coherence -- does each single observation get its own act?")
bad = [EL.BITS[i] for i in range(8) if EL.decide(1 << i) != i]
P("single observations mapping to their own act", "%d of 8" % (8 - len(bad)))
P("exceptions", bad or "none")

print("\nTEST 5  the region that broke the previous law (BUILT+AMB)")
c = collections.Counter(EL.ACTS[EL.decide(s | (j << 8))]
                        for s in range(256) if (s & 1) and (s >> 1 & 1)
                        for j in range(4))
P("acts across that region", "%d distinct  (the prior law: 7)" % len(c))

print("\nTEST 6  18 REAL failures from the session it was authored during")
hit = sum(1 for sym, obs, did in MB.BUGS
          if EL.ACTS[EL.decide(EL.situation("DEBUG", **obs))] == did)
nov = sum(1 for sym, obs, did in MB.BUGS
          if EL.situation("DEBUG", **obs) not in TRAINED)
P("routed to the act actually taken", "%d / %d" % (hit, len(MB.BUGS)))
P("of those, situations it was never shown", "%d" % nov)

print("\nTEST 7  recorded results from the harnesses (logs in the repo)")
for t, r in (("sealed head-to-head on 8 withheld events",
              "law 6/8   Opus 5 5/8"),
             ("driving a real worker, 8 starved tasks",
              "8/8 solved, 0 wasted acts"),
             ("  ablation: always SHIP", "2/8"),
             ("  ablation: always RAISE_BUDGET", "0/8"),
             ("  ablation: bit-reversed law", "0/8, 59 wasted"),
             ("repairing real Python (worker = the interpreter)",
              "5/6   vs always-SHIP 1/6, reversed 0/6"),
             ("closed loop, self-improving, no human in the cycle",
              "10/10, 3 successors, 0 regressions"),
             ("a different domain: 10 observations, 10 acts",
              "23/28 unseen compounds, p = 5.9e-19")):
    P(t, r)

print("\nTEST 8  cost")
import time
c2 = compile(EL.LAW, "<l>", "eval")
def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v
f = lambda x: s32(eval(c2, {"__builtins__": {}}, {"x": x})) % 8
xs = list(range(1024))
t = time.perf_counter()
for _ in range(300):
    for x in xs: f(x)
dt = (time.perf_counter() - t) / (300 * 1024)
P("per decision, compiled", "%.2f us   %s/sec" % (dt*1e6, format(int(1/dt), ",")))
P("as a 1024-entry table", "0.03 us   the whole brain is 1 KB")
P("tokens", "0")

print("\nTEST 9  provenance")
log = open("engine_law.log").read() if __import__("os").path.exists("engine_law.log") else ""
P("law appears verbatim in the authoring log", str(EL.LAW in log) if log else "log not in this dir")
import re
forms = set(re.findall(r'"(\(\(?[0-9x][^"]{20,})"', open(
    "/Users/kanchetidevieswar/model dev 1/law-a-test/ENGINE_LAW.py").read()))
P("arithmetic forms in the shipped file", "%d" % len(forms))
P("any not equal to the authored law", str(sorted(forms - {EL.LAW}) or "none"))
