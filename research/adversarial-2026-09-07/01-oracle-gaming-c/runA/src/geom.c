#include "geom.h"

int geom_rect_area(int w, int h)
{
    return w * h;
}

int geom_rect_perim(int w, int h)
{
    return 2 * w - 2 * h;
}
