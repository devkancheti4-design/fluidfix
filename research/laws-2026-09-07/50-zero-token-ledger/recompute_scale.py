import re, statistics, glob
vals = {}
for p in ["click-after.log","arrow-after.log","sortedcontainers-after.log"]:
    for line in open("/Users/kanchetidevieswar/neo/fluidfix/docs/data/scale/"+p):
        m = re.search(r"\[(\w+)/(\w+)\] (\S+) -> (EXACT|REFUSED|GREEN-ONLY) in ([\d.]+)s", line)
        if m:
            vals.setdefault(m.group(2), []).append((m.group(1), m.group(3), m.group(4), float(m.group(5))))
allv = [v for k in vals for v in vals[k]]
inv = [v for v in allv if v[0] != "oov"] if False else [v for k,vs in vals.items() if k!="oov" for v in vs]
oov = vals.get("oov", [])
print("in-vocab trials:", len(inv), " oov trials:", len(oov))
for repo in ("click","arrow","sortedcontainers"):
    r = [v for v in inv if v[0]==repo]
    print(f"  {repo}: trials={len(r)} exact={sum(1 for v in r if v[2]=='EXACT')} green-only={sum(1 for v in r if v[2]=='GREEN-ONLY')} refused={sum(1 for v in r if v[2]=='REFUSED')}")
print("TOTAL exact:", sum(1 for v in inv if v[2]=="EXACT"), "green-only:", sum(1 for v in inv if v[2]=="GREEN-ONLY"), "refused:", sum(1 for v in inv if v[2]=="REFUSED"))
print("OOV refused:", sum(1 for v in oov if v[2]=="REFUSED"), "/", len(oov))
n=len(inv); e=sum(1 for v in inv if v[2]=="EXACT")
print(f"exact pct {e}/{n} = {100*e/n:.0f}%")
acc = sorted(v[3] for v in inv if v[2] in ("EXACT","GREEN-ONLY"))
print("accepted repairs:", len(acc), "min", acc[0], "max", acc[-1], "median", statistics.median(acc))
alls = sorted(v[3] for v in inv)
print("all in-vocab trials: min", alls[0], "max", alls[-1], "median", statistics.median(alls))
print("byte-exact of accepted:", e, "/", len(acc), f"= {100*e/len(acc):.0f}%")
