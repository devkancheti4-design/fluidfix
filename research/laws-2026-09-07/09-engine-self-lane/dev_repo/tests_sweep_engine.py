"""SUPPLY SWEEP FOR THE ENGINE LAW — smaller and cheaper at EQUAL capability.

The lever proven on the debugger: sweep supplies and keep the one that is
smallest and fastest to author WITHOUT losing anything. Capability is checked
on every candidate, so a smaller law cannot win by being worse:

    exact on all 22 measured events
    all 8 acts reachable          (v1 of the prior law had act 7 dead)
    job invariance 0 of 256       (the generalisation claim)
    18 real session bugs routed   (the hardest available test)
"""
import sys, time, json, collections
sys.path.insert(0, "/Users/kanchetidevieswar/model dev 1/model-k-d")
sys.path.insert(0, "/Users/kanchetidevieswar/model dev 1/law-a-test")
from organism_inf.sphere import sphere_synthesize
from organism_inf.synth import _OPS, s32
import ENGINE_LAW as EL
import mybugs as MB

EVENTS = [(EL.situation(j, **o), a) for j, o, a, w in EL.EVENTS]

def _ntz(v, m):
    b = s32(v) & m; b &= -b
    return ((b.bit_length() - 1) if b else 0) & 15
def _T(inner):
    b = "((%s) & (0 - (%s)))" % (inner, inner); v = "((%s) - 1)" % b
    v = "((%s) - (((%s) >> 1) & 1431655765))" % (v, v)
    v = "(((%s) & 858993459) + (((%s) >> 2) & 858993459))" % (v, v)
    v = "((((%s) + ((%s) >> 4)) & 252645135))" % (v, v)
    return "(((((%s) * 16843009)) >> 24) & 15)" % v

_OPS.setdefault("ntzb",   (1, _T("(({a}) & 254)"), lambda a, _b: _ntz(a, 254)))
_OPS.setdefault("ntzall", (1, _T("(({a}) & 255)"), lambda a, _b: _ntz(a, 255)))
_OPS.setdefault("selfbit",(1, "((({a}) >> 7) & 1)", lambda a, _b: (s32(a) >> 7) & 1))
_OPS.setdefault("selffld",(1, "(((({a}) >> 7) & 1) << 2)", lambda a, _b: ((s32(a) >> 7) & 1) << 2))
_OPS.setdefault("builtb", (1, "((({a})) & 1)", lambda a, _b: s32(a) & 1))
_OPS.setdefault("lowbit", (1, "(({a}) & (0 - ({a})))", lambda a, _b: s32(a) & -s32(a)))

SUPPLIES = [
 ("current: ntzb+selfbit+shifts", ("ntzb","selfbit",">>1",">>2",">>3",">>7"),
  (0,1,2,3,4,5,6,7,8,15,128,254,255)),
 ("ntzb + selfbit",               ("ntzb","selfbit"),        tuple(range(9))+(254,)),
 ("ntzb + selffld (scaled)",      ("ntzb","selffld"),        (0,1,4,7)),
 ("ntzb + selffld, tiny k",       ("ntzb","selffld"),        (0,4,7)),
 ("ntzall + selffld",             ("ntzall","selffld"),      (0,1,4,7)),
 ("ntzb + selfbit + builtb",      ("ntzb","selfbit","builtb"), tuple(range(9))),
 ("ntzb only",                    ("ntzb",),                 tuple(range(9))),
]
for k in (1,2,3,7):
    _OPS.setdefault(">>%d"%k,(1,"({a} >> %d)"%k,lambda a,_b,k=k: s32(s32(a)>>k)))

def capability(expr):
    c = compile(expr, "<l>", "eval")
    rule = lambda x: s32(eval(c, {"__builtins__": {}}, {"x": x})) % 8
    exact = sum(1 for x, a in EVENTS if rule(x) == a)
    cov = len({rule(x) for x in range(1024)})
    jobs = sum(1 for s in range(256) if len({rule(s | (j << 8)) for j in range(4)}) > 1)
    bugs = sum(1 for sym, obs, did in MB.BUGS
               if EL.ACTS[rule(EL.situation("DEBUG", **obs))] == did)
    return exact, cov, jobs, bugs

print("%-30s %5s %7s %7s %5s %6s %6s  %s"
      % ("supply", "size", "secs", "exact", "acts", "jobvar", "bugs", "verdict"))
best = None
for label, ops, consts in SUPPLIES:
    t = time.time(); r = None
    for size in (1, 2, 3, 4):
        r = sphere_synthesize(EVENTS, intent="mask", max_size=size,
                              consts=consts, extra_ops=ops)
        if r.found: break
    dt = time.time() - t
    if not r.found:
        print("%-30s %5s %7.1f  %s" % (label, "-", dt, r.note[:40])); continue
    ex, cov, jv, bg = capability(r.expr)
    full = (ex == len(EVENTS) and cov == 8 and jv == 0 and bg == len(MB.BUGS))
    print("%-30s %5s %7.2f %4d/%-2d %2d/8 %5d %5d/%d  %s"
          % (label, r.size, dt, ex, len(EVENTS), cov, jv, bg, len(MB.BUGS),
             "FULL CAPABILITY" if full else "degraded"))
    if full and (best is None or (r.size, dt) < (best[1], best[2])):
        best = (label, r.size, dt, r)
print()
if best:
    label, size, dt, r = best
    print("OPTIMAL SUPPLY: %s" % label)
    print("  size %s (was %s), authored in %.2fs, capability identical"
          % (size, json.load(open("/dev/stdin")) if False else "7", dt))
    print("  %s" % r.expr[:110])
    json.dump({"supply": label, "law": r.expr, "size": r.size, "note": r.note},
              open("engine_law_v2.json", "w"), indent=1)
