"""Re-run the guard's own per-file loop, printing each RepairResult.
Uses fluidfix's public functions only; nothing is patched."""
import sys, time
sys.path.insert(0,"/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle, build_packet_c, find_candidate_files_c
from fluidfix.observers import MechanicalObserver
from fluidfix.loop import repair
root=sys.argv[1]
o=COracle(root, test_cmd="./build/tests", timeout=300)
fails,out=o.failing_output()
cands=find_candidate_files_c(o,out)
print("candidate files:",cands)
for rel in cands:
    pkt=build_packet_c(o,rel,out)
    if pkt is None: print(rel,"-> no packet"); continue
    obs=MechanicalObserver().observe([pkt])[0]
    print(f"\n=== {rel} (mode={pkt.mode}) obs={[(x.lineno,x.kinds) for x in obs]}")
    r=repair(o,rel,obs)
    print(f"  repaired={r.repaired} ambiguous={r.ambiguous} runs={r.suite_runs} acts={r.acts_tried}")
    print(f"  greens={r.greens}")
    print(f"  reason={r.reason}")
    for t in r.tried_log: print("   rejected:",t['at'],t['tried'],'|',str(t['why'])[:70])
    if r.repaired:
        print("  SHIPPED", r.lineno, r.new_line); break
