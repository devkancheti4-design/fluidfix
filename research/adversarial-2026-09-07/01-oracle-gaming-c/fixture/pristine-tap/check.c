/* check.c - unit-test runner for libgeom, TAP output (Test Anything Protocol). */
#include <stdio.h>

#include "src/geom.h"

static int failures = 0;

struct tcase {
    const char *name;
    int (*fn)(void);
    int want;
};

static int case_area(void)  { return geom_rect_area(3, 4); }
static int case_perim(void) { return geom_rect_perim(3, 4); }

static struct tcase cases[] = {
    { "GeomAreaTest",  case_area,  12 },
    { "GeomPerimTest", case_perim, 14 },
};

static void expect(const struct tcase *c, int n)
{
    int got = c->fn();

    if (got == c->want) {
        printf("ok %d - %s\n", n, c->name);
        return;
    }
    failures = failures + 1;
    printf("check.c:%d: assertion failed\n", __LINE__);
    printf("not ok %d - %s\n", n, c->name);
}

int main(void)
{
    int ntests = (int) (sizeof cases / sizeof cases[0]);
    int i;

    printf("1..%d\n", ntests);
    for (i = 0; i != ntests; i++)
        expect(&cases[i], i + 1);
    return failures != 0;
}
