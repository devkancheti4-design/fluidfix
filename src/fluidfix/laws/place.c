#include <stdio.h>
#include <stdint.h>

static inline int32_t L_LEFT (int32_t x) { return ((x + 24) >> 6); }
static inline int32_t L_RIGHT(int32_t x) { return (((x + 3) >> 3) - (x >> 3)); }

int32_t place(int32_t x) { return L_LEFT(x) | L_RIGHT(x); }   /* 0 TRAIL, 1 WRAP */

static int oracle(int L, int R) { return (L >= 5 || R >= 5) ? 1 : 0; }

int main(void)
{
    long tab = 0, tot = 0, rng = 0, mask_bad = 0, lanes = 0;
    int L, R, x, i;
    const uint64_t STATED = 0x7F7F6060606060ULL;
    uint64_t built = 0;

    for (L = 0; L <= 6; L++) for (R = 0; R <= 6; R++) {
        x = (L << 3) | R;
        if (place(x) != oracle(L, R)) tab++;
        if (place(x)) built |= (uint64_t)1 << x;
    }
    printf("  against the table, all 49 reachable        %ld\n", tab);
    printf("  the stated bitmask 0x7F7F6060606060        %s\n",
           built == STATED ? "reproduced" : "MISMATCH");
    if (built != STATED) { mask_bad = 1;
        printf("    built 0x%llX\n", (unsigned long long)built); }
    printf("  WRAP cases of the 49                       %d  (want 24)\n",
           __builtin_popcountll(built));
    if (__builtin_popcountll(built) != 24) mask_bad++;

    for (x = 0; x < 64; x++) { int a = place(x);
        if (a != 0 && a != 1) rng++; tot++; }
    printf("  total on 0..63, returns 0 or 1 only        %ld   (%ld words)\n", rng, tot);
    for (x = 0; x < 64; x++) {
        if (L_LEFT(x)  != (((x >> 3) >= 5) ? 1 : 0) && (x >> 3) <= 6) lanes++;
        if (L_RIGHT(x) != (((x & 7)  >= 5) ? 1 : 0) && (x & 7)  <= 6) lanes++; }
    printf("  each lane equals its own field's threshold %ld\n", lanes);

    {   const char *form[4] = { "last = len(x)          the taught shape",
                                "off + len(x)           associativity",
                                "min(99, len(x))        comma resets scope",
                                "k * len(x)             the defect" };
        const int FL[4] = {0, 4, 0, 5}, FR[4] = {0, 0, 0, 0};
        const int WANT[4] = {0, 0, 0, 1};
        long forms = 0;
        printf("\n  THE FOUR MEASURED FORMS\n");
        for (i = 0; i < 4; i++) {
            int a = place((FL[i] << 3) | FR[i]);
            if (a != WANT[i]) forms++;
            printf("    %-38s L=%d R=%d -> %s\n", form[i], FL[i], FR[i],
                   a ? "WRAP  (len(x) - 1) wrapped" : "TRAIL len(x) - 1"); }
        printf("    forms ruled wrongly                      %ld\n", forms);
        tab += forms;
    }

    {   int a = place((5 << 3) | 0);
        long inc = (a == 1) ? 0 : 1;
        printf("\n  THE RICH INCIDENT\n");
        printf("    L=5 (*)  R=0 (scope closes)  ->  %s\n", a ? "WRAP" : "TRAIL");
        printf("    ruled correctly                          %ld\n", inc);
        tab += inc;
    }

    printf("\n  TOTAL  %ld violations\n", tab + rng + mask_bad + lanes);
    return (tab + rng + mask_bad + lanes) != 0;
}
