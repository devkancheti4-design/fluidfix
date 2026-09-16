"""Fresh-process helper: print the file ranking the guard would use for the current red tree."""
import json, sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix import Oracle
from fluidfix.guard import find_candidate_files
o = Oracle(sys.argv[1], python=sys.executable)
red, out = o.failing_output()
ev = {}
ranked = find_candidate_files(o, out, limit=10, evidence=ev) if red else []
print(json.dumps({"red": red, "ranked": ranked, "pointed": ev.get("pointed", [])}))
