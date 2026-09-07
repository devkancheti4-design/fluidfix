/* Independent proof that the library is still wrong after the "repair". */
#include <stdio.h>
int geom_rect_area(int, int);
int geom_rect_perim(int, int);
int main(void) {
    printf("area(3,4)=%d (want 12)\nperim(3,4)=%d (want 14)\n",
           geom_rect_area(3, 4), geom_rect_perim(3, 4));
    return 0;
}
