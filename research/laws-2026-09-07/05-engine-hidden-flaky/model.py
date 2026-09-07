"""Analytic expectation for the sweep, from the code paths read in
src/fluidfix/loop.py (confirm loop, lines 357-397) and src/fluidfix/oracle.py
(check(): --lf fast gate, then full run; lines 185-240).

Fixture A (flaky test passes wrong code with prob q; anchor test deterministic,
first in file, so failing_output's -x leaves lastfailed={anchor}):
  check #1 on `b - a`: fast gate runs the anchor only -> pass (lastfailed
  cleared); full run: flaky test passes w.p. q.            -> q
  each of N confirm checks: fast gate now runs ALL tests (lastfailed empty)
  -> flaky w.p. q; full run -> flaky w.p. q.               -> q^2 each
  P(false accept) = q^(1+2N)
Fixture B (noisy test fails ANY code with prob r; anchor deterministic):
  `b - a` is rejected by the anchor at the fast gate, always.
  `a + b`: check #1 = anchor-only fast gate (pass) * full (1-r);
  each confirm = (1-r)^2.
  P(correct repair accepted) = (1-r)^(1+2N); refusal otherwise.
"""
q = 0.5
r = 0.5
print("fixture A  expected false-accept rate  = q^(1+2N), q=0.5")
for n in (0, 1, 2):
    print(f"  CONFIRM={n}: {q**(1+2*n):.4f}  ({100*q**(1+2*n):.2f}%)  -> expected in 50 runs: {50*q**(1+2*n):.1f}")
print("fixture B  expected correct-repair rate = (1-r)^(1+2N), r=0.5")
for n in (0, 1, 2):
    print(f"  CONFIRM={n}: {(1-r)**(1+2*n):.4f}  ({100*(1-r)**(1+2*n):.2f}%)  -> expected in 40 runs: {40*(1-r)**(1+2*n):.1f}")
