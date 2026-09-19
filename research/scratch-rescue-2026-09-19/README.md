# Rescued from the session scratchpad, 2026-09-19

These files lived only in a session scratchpad, which is temporary. They are committed here so a
scratchpad wipe does not destroy them. Nothing here was re-run or re-verified at rescue time.

## The HTML

`fluidnet.html` and `two-greens.html` **differ from the copies on `gh-pages-deploy`**, and which side is
newer could not be determined at rescue time — they are either pre-deploy drafts or post-deploy edits that
were never published. `taught-classes.html` and `fluidnet-site.html` are not on the deploy branch at all.

The published site is `gh-pages-deploy` (= `origin/gh-pages`, 6f29dcb). **Treat that branch as the source
of truth for what is live, and these as drafts** unless a diff shows otherwise.

## The scripts

Working scripts behind the 2026-09-18/19 experiments — dictionary construction, applier before/after
pairs, and the latent/divergence verification passes. Several carry hard-coded absolute paths into the old
scratchpad and will not run unmodified. They are kept as the record of what was actually executed, not as
a runnable harness.

| file | what it did |
|---|---|
| `verify_l1.py`, `verify_l23.py`, `final_check_l23.py` | the layered verification passes |
| `appliers_orig.py`, `appliers_fixed.py` | an applier before and after its audit |
| `make_dicts.py` | built the taught dictionaries used by a sweep |
| `patch_taught.py`, `patch_kindof.py` | the scripts that corrected published pages against later measurements |
| `fix_a.py`, `fix_b.py`, `check.py` | small A/B fixtures |
