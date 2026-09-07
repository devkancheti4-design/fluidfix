#include "fee.h"
#include "rate.h"

/* The customer's monthly bill: the metered usage fee plus the flat
 * monthly service charge, which the 2026-Q3 schedule fixes at 25 cents.
 */
int rate_total(int units)
{
    return fee_for(units) + 24;
}
