"""As-shipped probe: let coracle's _Coverage configure its own instrumented
tree (cov_dir 'covbuild_asshipped') and report what the gcov tier returns
on cglm. Run from the cglm copy: nice -n 15 ../to.sh 300 <venv>/python ../asshipped_probe.py"""
import os, time
from fluidfix.coracle import COracle, _Coverage
o = COracle(os.getcwd(), build_dir="build")
cov = _Coverage(o, cov_dir="covbuild_asshipped")
print("fast-build test_cmd:", o.test_cmd, "| build type mirrored:", cov._build_type())
t0 = time.time(); ok = cov._ensure_build(280)
print(f"_ensure_build ok={ok} in {time.time()-t0:.1f}s; _test_binary() -> {cov._test_binary()}")
t0 = time.time(); full = cov.lines()
print(f"cov.lines() -> {len(full)} files in {time.time()-t0:.2f}s")
cache = os.path.join("covbuild_asshipped", "CMakeCache.txt")
for line in open(cache):
    if line.startswith(("CGLM_USE_TEST", "CMAKE_BUILD_TYPE:", "CMAKE_C_FLAGS:")):
        print("  cache:", line.strip())
fast = os.path.join("build", "CMakeCache.txt")
for line in open(fast):
    if line.startswith("CGLM_USE_TEST"):
        print("  fast-build cache:", line.strip())
