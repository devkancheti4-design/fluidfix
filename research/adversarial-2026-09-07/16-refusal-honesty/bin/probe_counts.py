"""Count what a guard pass ACTUALLY tried, via the public api, and compare
with what the refusal report claims. No fluidfix source is modified."""
import sys, json, time
from fluidfix.oracle import Oracle
from fluidfix.localize import build_packet
from fluidfix.observers import MechanicalObserver
from fluidfix.guard import rank_observations
from fluidfix.loop import repair
root, rel = sys.argv[1], sys.argv[2]
o = Oracle(root)
fails, out = o.failing_output()
p = build_packet(o, rel)
obs = rank_observations("\n".join(p.src_lines),
                        MechanicalObserver().observe([p])[0], out,
                        root=o.root, rel=rel)
r = repair(o, rel, obs)
print(json.dumps({"repaired": r.repaired, "reason": r.reason,
                  "suite_runs": r.suite_runs,
                  "tried_log_len": len(r.tried_log),
                  "tried_more": r.tried_more,
                  "actually_rejected": len(r.tried_log) + r.tried_more,
                  "greens": len(r.greens)}, indent=1))
