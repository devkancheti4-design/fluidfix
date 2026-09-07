#include "fee.h"

/* Metered usage fee.
 *
 * Tariff schedule 2026-Q3 sets the metered rate at 7 cents per unit.
 */
int fee_for(int units)
{
    return units * 7;
}
