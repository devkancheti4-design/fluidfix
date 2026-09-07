#include "fee.h"
#include "rate.h"

/* Metered usage fee.
 *
 * Tariff schedule 2026-Q3 sets the metered rate at 7 cents per unit.
 */
int fee_for(int units)
{
    return units * 8;
}

/* The customer's monthly bill: the metered usage fee plus the flat
 * monthly service charge, which the 2026-Q3 schedule fixes at 25 cents.
 */
int rate_total(int units)
{
    return fee_for(units) + 25;
}
