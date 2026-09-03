/* sight.c - THE SIGHT LAW. GENERATED; every expression authored by search.
 *
 * This is the authored kernel, vendored verbatim as provenance for
 * src/fluidfix/sight.py. The Python port must agree with the specification
 * below on all 256 inputs; tests/test_sight_law.py and `fluidfix selfcheck`
 * both enforce that. Build and run this file to check the kernel itself:
 *
 *     cc -O2 -o sight docs/laws/sight.c && ./sight
 *
 * For ONE candidate source file, how soon should it be opened when the test
 * suite has gone red?  Input: one byte of observations, all mechanically
 * measurable before any candidate is tried.  Output: priority 0..7, lower first.
 *
 *   bit 0  FRAMED      the failing traceback names this file      POINTING
 *   bit 1  SCARCE      the class signal matches <= 2 files        POINTING
 *   bit 2  LITERAL     an asserted literal occurs in <= 2 files   POINTING
 *   bit 3  FAILONLY    specificity >= 0.9                        circumstantial
 *   bit 4  NAMED       filename shares a token with the test     circumstantial
 *   bit 5  TOUCHED     modified in the last 40 commits           circumstantial
 *   bit 6  SMALL       0 < executed lines < 80                   circumstantial
 *   bit 7  UBIQUITOUS  specificity < 0.25                        penalty
 *
 * WHY R1 AND R2 HOLD STRUCTURALLY
 *
 * They are not enforced by cases; they are consequences of where the bits sit.
 * POINTING owns mask bit 0 and every circumstantial slot owns a bit >= 2, so
 * ctz of any mask carrying pointing evidence is 0 while ctz of any mask without
 * it is at least 2 - no quantity of circumstantial evidence can close that gap,
 * because the slots it can set are strictly above bit 0.  That is R1.  For R2,
 * both the circumstantial sum and the demotion term are ANDed with
 * gate = POINT1 - 1, which is identically zero whenever a pointing bit is set;
 * the penalty is therefore unreachable on a pointed-at file by the algebra of
 * the expression, not by a test that could be written the wrong way round.
 *
 * No filename, repository or fault class appears anywhere below.  The law reads
 * the SITUATION of the evidence, never the content of the code.
 */
#include <stdio.h>
#include <stdint.h>
#include <time.h>

/* ---- authored lanes ---- */
static inline int32_t POINT1(int32_t x) { return ((0 - (x >> 3)) + ((x + 7) >> 3)); }   /* any pointing bit */
static inline int32_t FAILONLY (int32_t x) { return ((2 & (x >> 2)) + (2 & (x >> 2))); }  /* -> mask bit 2 */
static inline int32_t NAMED    (int32_t x) { return (8 & (x >> 1)); }  /* -> mask bit 3 */
static inline int32_t TOUCHED  (int32_t x) { return ((8 & (x >> 2)) + (8 & (x >> 2))); }  /* -> mask bit 4 */
static inline int32_t SMALL    (int32_t x) { return ((63 & (x >> 1)) - (31 & (x >> 1))); }  /* -> mask bit 5 */
static inline int32_t UBIQ(int32_t x) { return (x >> 7); }

/* authored for "which token do I write next", unchanged since */
static inline int32_t EMIT(int32_t m) { return m & (-m); }

#define FLOOR 64                      /* no evidence at all -> mask bit 6 */

int32_t sight(int32_t obs)
{
    int32_t p    = POINT1(obs);
    int32_t gate = p - 1;             /* 0 when pointing, all-ones when not */
    int32_t circ = FAILONLY(obs) + NAMED(obs) + TOUCHED(obs) + SMALL(obs);
    int32_t mask = p + (gate & circ) + FLOOR;
    return __builtin_ctz(EMIT(mask)) + (gate & UBIQ(obs));
}

/* ================= exhaustive self-check ================= */
static int32_t spec(int32_t x)
{
    if (x & 7) return 0;
    if ((x >> 3) & 1) return 2 + ((x >> 7) & 1);
    if ((x >> 4) & 1) return 3 + ((x >> 7) & 1);
    if ((x >> 5) & 1) return 4 + ((x >> 7) & 1);
    if ((x >> 6) & 1) return 5 + ((x >> 7) & 1);
    return 6 + ((x >> 7) & 1);
}

int main(void)
{
    long wrong = 0, r1 = 0, r2 = 0, r3 = 0;
    for (int32_t x = 0; x < 256; x++) if (sight(x) != spec(x)) wrong++;
    printf("  specification, all 256 inputs        %ld wrong\n", wrong);

    /* R1: any pointing file outranks every non-pointing file */
    for (int32_t a = 0; a < 256; a++) { if (!(a & 7)) continue;
        for (int32_t b = 0; b < 256; b++) { if (b & 7) continue;
            if (!(sight(a) < sight(b))) r1++; } }
    printf("  R1  pointing outranks non-pointing    %ld violations\n", r1);

    /* R2: UBIQUITOUS never changes the answer for a pointed-at file */
    for (int32_t x = 0; x < 256; x++)
        if ((x & 7) && sight(x) != sight(x & 0x7f)) r2++;
    printf("  R2  UBIQUITOUS never demotes pointing  %ld violations\n", r2);

    /* R3: within a tier, more evidence is never worse */
    for (int32_t x = 0; x < 256; x++)
        for (int b = 0; b < 7; b++)
            if (!((x >> b) & 1) && sight(x | (1 << b)) > sight(x)) r3++;
    printf("  R3  monotone in the evidence bits      %ld violations\n", r3);

    /* the three incidents */
    int32_t LIT = 1<<2, SCA = 1<<1, NAM = 1<<4, UBI = 1<<7;
    long inc = 0;
    if (sight(LIT)       != 0) inc++;   /* 1  LITERAL alone -> first */
    if (sight(SCA|UBI)   != 0) inc++;   /* 2  SCARCE survives UBIQUITOUS */
    if (!(sight(SCA|UBI) < sight(NAM))) inc++;  /* 2  and beats NAMED */
    if (sight(0)         != 6) inc++;   /* 3  no evidence -> low class */
    printf("  the three incidents                    %ld violations\n", inc);

    /* every evidence-free file must share one class: no invented winner */
    long distinct = 0; int seen[8] = {0};
    for (int32_t x = 0; x < 256; x++)
        if (!(x & 7) && !(x & 0x78)) seen[sight(x)] = 1;
    for (int i = 0; i < 8; i++) distinct += seen[i];
    printf("  evidence-free files span              %ld classes (UBIQ splits 6/7)\n", distinct);

    volatile int32_t sink = 0;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (long r = 0; r < 4000000L; r++)
        for (int32_t x = 0; x < 256; x++) sink += sight(x);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double ns = ((t1.tv_sec-t0.tv_sec)*1e9 + (t1.tv_nsec-t0.tv_nsec))/(4000000.0*256.0);
    printf("  %.2f ns per candidate file  (sink %d)\n", ns, sink);

    printf("\n  TOTAL  256 inputs  %ld violations\n", wrong+r1+r2+r3+inc);
    return (wrong+r1+r2+r3+inc) != 0;
}
