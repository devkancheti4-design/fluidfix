"""What the SIGHT lanes actually read, via the public api."""
import sys, json
from fluidfix.oracle import Oracle
from fluidfix.guard import find_candidate_files
root = sys.argv[1]
o = Oracle(root)
fails, out = o.failing_output()
ev = {}
c = find_candidate_files(o, out, evidence=ev)
print(json.dumps({"candidates": c, "evidence": ev,
                  "raw_failing_output_has_source_frame":
                      any(l.strip().startswith("pkg/") for l in out.splitlines())},
                 indent=1))
