# Agent 38 — counterfactual: does the ruling at guard.py:539 CHANGE the outcome?
#
# Rebinds fluidfix.engine.decide so that the ONE live consultation reached
# from guard_once (guard.py:539, byte CAPPED|REFUTED = 0x60) returns
# HARVEST_COUNTEREXAMPLE instead of the law's RAISE_BUDGET. Every other
# consultation is left exactly as the law rules. Nothing in src/ is edited.
#
# Loaded with `pytest -p counterfactual_plugin`. Run the SAME test that
# passes under the real law; a failure here proves the ruling is load-bearing.
import traceback


def pytest_configure(config):
    import fluidfix
    from fluidfix import engine, guard, loop
    real = engine.decide

    def decide(sit):
        out = real(sit)
        st = traceback.extract_stack()
        caller = st[-2]
        if caller.filename.endswith("guard.py") and out == "RAISE_BUDGET":
            print("[cf] suppressing RAISE_BUDGET at guard.py:%d (byte 0x%02x)"
                  % (caller.lineno, sit & 0xFF))
            return "HARVEST_COUNTEREXAMPLE"
        return out
    engine.decide = decide
    loop.decide = real          # loop's own consultations stay honest
    _ = (fluidfix, guard)
