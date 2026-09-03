# Prompt: author the SIGHT law (instant localisation)

Author a branchless kernel that decides, for ONE candidate source file,
how soon it should be opened when a test suite has gone red.

    input   one byte of observations about that file, all mechanically
            measurable before any candidate is tried
    output  priority 0..7, lower is opened first

## The observation byte

    bit  name         meaning (all measurable, none an opinion)
      0  FRAMED       the failing traceback names this file
      1  SCARCE       the taught class's signal regex matches lines in
                      <= 2 files repo-wide, and this is one of them
      2  LITERAL      a literal printed by the assertion occurs in this
                      file, and in <= 2 files repo-wide
      3  FAILONLY     specificity >= 0.9 (its executed lines come almost
                      only from the failing tests)
      4  NAMED        its filename shares a token with the failing test
                      module's name
      5  TOUCHED      modified by the last 40 commits
      6  SMALL        few executed lines (0 < n < 80): cheap to search
      7  UBIQUITOUS   specificity < 0.25: nearly every test executes it

## The structural requirement — two tiers

FRAMED, SCARCE and LITERAL are POINTING evidence: the failure itself, or
the taught class itself, indicating this file. NAMED, TOUCHED, SMALL and
FAILONLY are CIRCUMSTANTIAL.

    R1  Any file with >= 1 pointing bit outranks every file with none,
        no matter how much circumstantial evidence the latter carries.
    R2  UBIQUITOUS demotes ONLY among files with no pointing evidence.
        It must never demote a file the failure or the class points at.
    R3  Among files in the same tier, more evidence is never worse
        (monotone in the remaining bits).
    R4  Deterministic, branchless, no data-dependent loops, no tables.
        Verifiable exhaustively over all 256 inputs.

## The three incidents this law exists to settle

Each is real and measured on click 8.5.1; the law must produce the
stated ranking for each.

1. termui.py — assertion compared ANSI codes; the literal `95` occurs in
   exactly 1 of 17 files. No coverage or name signal distinguished it.
   Before literal evidence: rank #6, 1,740s, REFUSED.
   After: rank #1, 50s, byte-exact.
   REQUIRED: LITERAL alone puts it at priority 0.

2. types.py — defect at types.py:499. Failing module is
   test_shell_completion.py, and click HAS a shell_completion.py, so
   NAMED fired for the wrong file. types.py had no FRAMED, no NAMED, no
   LITERAL, and was UBIQUITOUS (every test executes it) — so the only
   discriminating lane pointed elsewhere while the defect file carried
   an active penalty. The taught class's signal regex
   `\.(startswith|endswith)\(` matches in few files: SCARCE is the lane
   that should have decided it.
   REQUIRED: SCARCE beats NAMED, and UBIQUITOUS does not demote a
   SCARCE file. types.py must rank above shell_completion.py.

3. _textwrap.py — no frame, no literal, no name overlap, no scarcity.
   Genuinely undecidable from evidence.
   REQUIRED: the law must NOT invent a winner. Every such file lands in
   the same low-priority class, and the caller is free to report an
   honest search limit rather than a false lead.

## Deliverables

- `sight.c`: the kernel. Same shape as rank.c — evidence lanes folded
  into a sum, one EMIT, priority from the low bit.
- A one-paragraph derivation of why R1 and R2 hold structurally, not by
  case analysis.
- An exhaustive self-check over all 256 inputs asserting R1, R2, R3, and
  the three incidents above.

Do not encode any filename, any repo, or any fault class. The law reads
the SITUATION of the evidence, never the content of the code.
