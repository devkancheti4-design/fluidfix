# Teach one shape, test on novel and real — 2026-09-22

**The shape:** an attribute looked up on a receiver by the wrong name, where the right name is a *sibling*
the receiver actually has. Chosen because it recurs in real history as code, not text: `kwargs.get` →
`.pop`, `cls.fromdate` → `.fromdatetime`, `term.partition` → `.rpartition`, `self.fail` → `.error`.

**Taught from one worked example**, click `dce3b868` (`self.fail(...)` → `self.error(...)`), by hand.
Candidates come from three places the file itself can vouch for — other attributes used on the same
receiver, functions the file defines, the wrong name's own builtin family — ranked by string similarity,
and the suite picks. Its property: *the rewrite changes exactly one token, that token is an attribute name
after a dot, and nothing else on the line moves.* Controls: one attribute change PROVEN; two tokens,
a changed receiver, and a name not after a dot all REFUTED.

`examples/taught-2026-09-22/sibling_attribute.py`

## Novel shapes — 84 of 84, all exact, zero wrong accepts

Generated instances, names and values and **syntactic position** all varying, none ever shown to the
class. Each file defines four siblings with distinct behaviour and the function calls the wrong one. The
suite is the judge, and — as a real suite would — it asserts every sibling's own behaviour, not just the
call site.

| position (never taught) | repaired | exact fix |
|---|---|---|
| `return recv.m()` | 12/12 | 12/12 |
| `v = recv.m() + k` | 12/12 | 12/12 |
| `twice(recv.m())` | 12/12 | 12/12 |
| `out.append(recv.m())` | 12/12 | 12/12 |
| `if recv.m() > k:` | 12/12 | 12/12 |
| `{'v': recv.m()}` | 12/12 | 12/12 |
| `self.m()` inside a class | 12/12 | 12/12 |
| **all seven** | **84/84** | **84/84** |

Negative control — twelve files whose bug is an off-by-one, not a wrong attribute, in code full of
dotted calls: the class fires on every one and the suite accepts **0 of 12** of its candidates.

Two things the first run got wrong, both in the *harness*, both fixed before these numbers:

- My single-assertion tests let the shipped `literal-off-by-one` class go green by editing the wrongly
  called method's *definition* (`items[0]` → `items[-1]`) instead of the call site. One assertion per
  sibling — what any real suite has — turns that into a NO-COLLATERAL rejection. 72/84 → 84/84.
- On `out.append(recv.m())` the applier emitted all ten of `out.append`'s list-family siblings before
  any of `recv.m`'s file-defined ones; the research harness caps candidates at 8, so the right one sat
  at position 12 and was never tried. 3/12 → 12/12 after interleaving across attributes, file-evidenced
  pools first. The SQLAlchemy note in `acts.py` said it two weeks ago: the cap, not the knowledge, binds.

## Real shapes — the knowledge reaches 8 of 15; every miss is the same boundary

Held-out real commits against their actual parent-commit files. The corpus ships no tests for these, so
this is the knowledge question: is the maintainer's exact line among the class's candidates, and at what
rank. Five were held out when the class was written; ten more were found afterwards by scanning all 565
fixes, and were not consulted for anything.

| | n | right name in the file's evidence | rank ≤ 8 (harness cap) | rank ≤ 32 (product cap) |
|---|---|---|---|---|
| held out when taught | 5 | 4 | 2 | 4 |
| found afterwards | 10 | 4 | 3 | 4 |
| **both** | **15** | **8** | **5** | **8** |

Under the product's cap, **every case where the file contains the sibling is reached.** The seven misses
are one boundary: the right name is defined on a type from *another module* — `Path().resolve` →
`.absolute` (pathlib), `.clear_output` → `.close` (ipywidgets), `box.left` → `.mid_left`, `triplet.css` →
`.hex` — or the line is a docstring. File-local evidence cannot see across an import. That is a stated
limit of this class, not of the mechanism; a class fed the receiver's type would have the pool.

| sha | wrong → right | pool | rank |
|---|---|---|---|
| `dce3b868` taught | fail → error | 67 | 63 |
| `f872d7a5` | get → pop | 12 | 12 |
| `877cd149` | fromdate → fromdatetime | 45 | 1 |
| `16cd686b` | ceil → floor | 43 | 16 |
| `e1c105b8` | partition → rpartition | 46 | 1 |
| `9e81697c` | _dict → _view | 22 | 3 |
| `75c64628` | foot_left → foot_right | 12 | 1 |
| `ed59a76f` | join → stop | 103 | 14 |
| `a73d23a7` docstring | SQUARE → ROUNDED | 6 | 1 |

## A ranking change, pre-registered, tested blind, and not adopted

Three of the five in-pool held-out fixes share almost no letters with the wrong name, and the taught
example's own fix ranks 63rd of 67 by similarity. Real wrong-attribute bugs are semantic siblings, not
typos. So a second ranking was written down *before* the ten fresh cases were looked at: same-receiver
names by how often the file uses them, then file-defined names by frequency, then the builtin family,
similarity as tiebreak.

On the fresh ten it **ties at ≤ 8 (3 vs 3) and loses at ≤ 32 (3 vs 4)** — it rescues `fail → error` and
buries `ceil → floor` (16 → 38) and `join → stop` (14 → 34). It stays out. The weakness it was meant to
fix is real and is left open rather than tuned to fifteen data points.

## Honest boundaries

- Novel instances are generated; they show the shape generalises across position, not how often it occurs.
- Real cases are the knowledge question — reached, not certified. No suite ran on them.
- The research harness caps at 8 candidates per line and the product at 32; both columns are shown.
- Cross-file attribute knowledge is out of scope for this class as written.
