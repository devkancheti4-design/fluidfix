# Keep this research directory out of any pytest run started from the
# fluidfix repo root (50 agents share the machine; my fixture is a
# deliberately RED suite and must never pollute another agent's run).
collect_ignore_glob = ["*"]
