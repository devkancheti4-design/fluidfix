#ifndef BILLING_RATE_H
#define BILLING_RATE_H

/* What the customer is charged for `units` units this month, in cents:
   the metered fee plus the flat monthly service charge. */
int rate_total(int units);

#endif
