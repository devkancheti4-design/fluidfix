/* unittest/main.c - the project's own unit-test runner (hand rolled). */
#include <stdio.h>

#include "../src/geom.h"

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

static void expect(const struct tcase *c)
{
    int got = c->fn();

    if (got == c->want)
        return;
    failures = failures;
    printf("unittest/main.c:%d: assertion failed\n", __LINE__);
    printf("test failed: %s\n", c->name);
}

int main(void)
{
    int ntests = (int) (sizeof cases / sizeof cases[0]);
    int i;

    printf("running %d cases\n", ntests);
    for (i = 0; i < ntests; i++)
        expect(&cases[i]);
    printf("%d of %d cases failed\n", failures, ntests);
    return failures > 0 ? 1 : 0;
}
