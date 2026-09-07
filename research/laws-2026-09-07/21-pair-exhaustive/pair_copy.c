/* pair.c - THE PAIR LAW. GENERATED; every expression authored by search.
 *
 * When a single-edit search has failed, decide whether to attempt MORE THAN
 * ONE simultaneous edit - and in what form.  Input: one byte of observations
 * measurable after a completed single-edit search.  Output: priority 0..7,
 * lower is attempted first.
 *
 *   bit 0  EXHAUSTED  every single-edit candidate tried and rejected
 *   bit 1  PARTIAL    some single edit strictly REDUCED the failing count
 *   bit 2  DISJOINT   the failing tests partition into disjoint sites
 *   bit 3  COUPLED    every failing test touches the same site
 *   bit 4  CHEAP      the candidate space is affordable
 *   bit 5  TAUGHT     the classes were taught from worked examples
 *   bit 6  CANCELING  a pair is green JOINTLY while each member alone leaves
 *                     the suite red AND reduces nothing
 *   bit 7  CAPPED     clean inputs, budget already spent
 *
 *   0 PARTITION  1 PAIR  2 WIDEN  3 TEACH  4 BUDGET  5 CAPPED  6 SINGLE  7 REFUSE
 *
 * WHY R1, R2 AND R3 HOLD STRUCTURALLY
 *
 * None of the three is enforced by a case; each is a consequence of the
 * algebra.  R1: every action slot is ANDed with gr = 0 - READY, which is
 * identically zero until EXHAUSTED is set, so the multi-edit lanes are not
 * merely unlikely to fire while a single edit remains untried - they are
 * algebraically absent from the word.  R2: PARTITION owns mask bit 0 and PAIR
 * owns bit 1, so ctz returns the partition whenever one exists, whatever else
 * is true; the quadratic answer cannot outrank the linear one by position, not
 * by comparison.  R3: on CANCELING both gb and gc are zero, so every lane
 * vanishes and only the floor at bit 7 survives - a compensating pair reaches
 * last place not because a rule demotes it but because nothing else is left in
 * the mask.  A pair search is a machine for finding two bugs that cancel, so
 * "green only in combination" is treated as suspicion and never as success.
 *
 * No filename, repository or fault class appears below.  The law reads the
 * SITUATION of the search, never the content of the code.
 *
 * This law does NOT decide whether an accepted repair ships.  That remains the
 * engine law (BUILT / AMB / CAPPED); a pair that is found and accepted faces
 * the same ambiguity test as any single candidate.
 */
#include <stdio.h>
#include <stdint.h>
#include <time.h>

/* ---- authored lanes ---- */
static inline int32_t READY    (int32_t x) { return (x & 1); }
static inline int32_t CANCEL   (int32_t x) { return (1 & (x >> 6)); }
static inline int32_t BLOCK    (int32_t x) { return (((x + 64) >> 7) - ((x + 64) >> 8)); }
static inline int32_t PARTITION(int32_t x) { return (1 & (x >> 2)); }
static inline int32_t PARTIAL  (int32_t x) { return (1 & (x >> 1)); }
static inline int32_t COUPLED  (int32_t x) { return (1 & (x >> 3)); }
static inline int32_t CHEAP2   (int32_t x) { return ((1 & (x >> 4)) + (1 & (x >> 4))); }
static inline int32_t NOTCOUP  (int32_t x) { return ((2 - (x >> 2)) + (2 ^ (x >> 2))); }
static inline int32_t TEACH    (int32_t x) { return (8 - (8 & (x >> 2))); }
static inline int32_t BUDGET   (int32_t x) { return (16 - (x & 16)); }
static inline int32_t CAPPED_L (int32_t x) { return ((15 ^ (x >> 3)) - (15 - (x >> 3))); }
static inline int32_t SINGLE   (int32_t x) { return ((32 - (x << 5)) + (32 ^ (x << 5))); }

/* authored for "which token do I write next", unchanged since */
static inline int32_t EMIT(int32_t m) { return m & (-m); }

#define FLOOR 128

int32_t pair_law(int32_t obs)
{
    int32_t gr  = 0 - READY(obs);      /* all-ones only when EXHAUSTED  */
    int32_t gc  = CANCEL(obs) - 1;     /* all-ones only when NOT cancel */
    int32_t gb  = BLOCK(obs) - 1;      /* all-ones only when neither    */
    int32_t gp  = 0 - PARTIAL(obs);    /* all-ones only when PARTIAL    */
    int32_t gcp = 0 - COUPLED(obs);    /* all-ones only when COUPLED    */

    int32_t pair  = gp & gcp & CHEAP2(obs);
    int32_t widen = gp & NOTCOUP(obs);
    int32_t act   = gr & (PARTITION(obs) + pair + widen
                          + TEACH(obs) + BUDGET(obs));
    int32_t mask  = (gb & (act + SINGLE(obs))) + (gc & CAPPED_L(obs)) + FLOOR;
    return __builtin_ctz(EMIT(mask));
}

/* ================= exhaustive self-check ================= */
#define EXH 1
#define PAR 2
#define DIS 4
#define COU 8
#define CHE 16
#define TAU 32
#define CAN 64
#define CAP 128

static int32_t spec(int32_t x)
{
    if (x & CAN) return 7;
    if (!(x & CAP)) {
        if (x & EXH) {
            if (x & DIS) return 0;
            if ((x & PAR) && (x & COU) && (x & CHE)) return 1;
            if ((x & PAR) && !(x & COU)) return 2;
            if (!(x & TAU)) return 3;
            if (!(x & CHE)) return 4;
        } else return 6;
    }
    if (x & CAP) return 5;
    return 7;
}

int main(void)
{
    long wrong=0, r1=0, r2=0, r3=0, r4=0, r5=0, inc=0;
    for (int32_t x = 0; x < 256; x++) {
        int32_t g = pair_law(x);
        if (g != spec(x)) wrong++;
        if (!(x & EXH) && g <= 4) r1++;                       /* R1 */
        if ((x & DIS) && (x & EXH) && !(x & CAN) && !(x & CAP) && g != 0) r2++;
        if ((x & CAN) && g != 7) r3++;                        /* R3 */
        if (g == 1 && !(x & PAR)) r4++;                       /* R4 */
        if (g == 1 && !(x & CHE)) r5++;                       /* R5 */
    }
    printf("  specification, all 256 inputs          %ld wrong\n", wrong);
    printf("  R1  no pair before EXHAUSTED           %ld violations\n", r1);
    printf("  R2  DISJOINT outranks a pair           %ld violations\n", r2);
    printf("  R3  CANCELING always ranks last        %ld violations\n", r3);
    printf("  R4  PAIR requires PARTIAL progress     %ld violations\n", r4);
    printf("  R5  PAIR never starts without CHEAP    %ld violations\n", r5);

    if (pair_law(PAR|COU|CHE|TAU|CAN)     != 7) inc++;
    if (pair_law(PAR|COU|CHE|TAU|CAN)     == 1) inc++;
    if (pair_law(EXH|TAU)                 != 4) inc++;
    if (pair_law(EXH|PAR|DIS|TAU|CHE)     != 0) inc++;
    if (pair_law(EXH|PAR|COU|CHE|TAU)     != 1) inc++;
    if (pair_law(0)                       != 6) inc++;
    printf("  the five incidents                     %ld violations\n", inc);

    long npair = 0;
    for (int32_t x = 0; x < 256; x++) if (pair_law(x) == 1) npair++;
    printf("  inputs that reach a PAIR search        %ld of 256\n", npair);

    volatile int32_t sink = 0;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (long r = 0; r < 4000000L; r++)
        for (int32_t x = 0; x < 256; x++) sink += pair_law(x);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double ns = ((t1.tv_sec-t0.tv_sec)*1e9 + (t1.tv_nsec-t0.tv_nsec))/(4000000.0*256.0);
    printf("  %.2f ns per decision  (sink %d)\n", ns, sink);

    printf("\n  TOTAL  256 inputs  %ld violations\n", wrong+r1+r2+r3+r4+r5+inc);
    return (wrong+r1+r2+r3+r4+r5+inc) != 0;
}
