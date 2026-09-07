import sys
sys.path.insert(0,"/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.coracle import COracle, build_packet_c, find_candidate_files_c
from fluidfix.observers import MechanicalObserver
from fluidfix.lanes import mask_of, HALT, EMIT, ADVANCE, kind_of
from fluidfix.acts import act_for, candidates
root=sys.argv[1]
o=COracle(root, test_cmd="./build/tests", timeout=300)
fails,out=o.failing_output()
print("candidates:", find_candidate_files_c(o,out))
pkt=build_packet_c(o,"src/rate.c",out)
print("packet mode:",pkt.mode,"lines:",pkt.lines)
obs=MechanicalObserver().observe([pkt])[0]
for ob in obs:
    print(f"line {ob.lineno} kinds={ob.kinds}  src={pkt.src_lines[ob.lineno-1]!r}")
    m=mask_of(k for k in ob.kinds if 0<=k<=15); seq=[]
    while not HALT(m):
        k=kind_of(EMIT(m)); m=ADVANCE(m); a=act_for(k)
        ob.all_lines=[l.rstrip("\r") for l in pkt.src_lines]
        seq.append((k,a,candidates(pkt.src_lines[ob.lineno-1].rstrip("\r"),a,ob)))
    for k,a,c in seq: print(f"   kind {k} -> act {a}: {c}")
