/* NOT part of the suite. Checks the shipped program against the 2026-Q3
   tariff documented in src/fee.c and src/rate.c: 7c per metered unit plus a
   flat 25c monthly service charge. */
#include <stdio.h>
#include "fee.h"
#include "rate.h"

int main(void)
{
    int bad = 0;
    printf("units  fee_for  spec(7*u)   rate_total  spec(7*u+25)\n");
    for (int u = 0; u <= 4; u++) {
        int f = fee_for(u), sf = 7 * u;
        int r = rate_total(u), sr = 7 * u + 25;
        printf("%5d  %7d  %9d   %10d  %12d   %s\n", u, f, sf, r, sr,
               (f == sf && r == sr) ? "ok" : "WRONG");
        if (f != sf || r != sr) bad++;
    }
    printf("flat service charge as shipped: rate_total(0) = %d (spec 25)\n",
           rate_total(0));
    printf("%d of 5 unit counts are billed wrongly\n", bad);
    return bad ? 1 : 0;
}
