#include <stdio.h>

#include "rate.h"
#include "tier.h"

static int failures;

static void check(const char *name, int got, int want, int line)
{
    if (got == want) {
        printf("ok      %s\n", name);
        return;
    }
    printf("test failed: %s\n", name);
    printf("tests/test_billing.c:%d: expected %d, got %d\n", line, want, got);
    failures++;
}

int main(void)
{
    /* regression: mid-volume customers are tier 2 */
    check("TierTest", tier_of(140), 2, __LINE__);
    /* regression INC-4471: one unit on the 2026-Q3 schedule bills 32c */
    check("RateTest", rate_total(1), 32, __LINE__);

    printf("%d of 2 checks did not pass\n", failures);
    return failures ? 1 : 0;
}
