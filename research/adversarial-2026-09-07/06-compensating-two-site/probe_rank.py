import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle, find_candidate_files_c, _c_sources
root = sys.argv[1]
o = COracle(root, test_cmd="./build/tests", timeout=300)
fails, out = o.failing_output()
print("red:", fails)
print("failing test names:", o._fail_tests)
print("sources seen:", _c_sources(root))
print("candidate order:", find_candidate_files_c(o, out))
