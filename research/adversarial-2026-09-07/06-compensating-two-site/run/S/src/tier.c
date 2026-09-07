#include "tier.h"

/* Volume tier for a month's consumption. */
int tier_of(int units)
{
    if (units < 100)
        return 1;
    if (units < 500)
        return 2;
    return 3;
}
