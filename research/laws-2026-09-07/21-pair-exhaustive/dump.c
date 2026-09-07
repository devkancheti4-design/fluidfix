#include "pair_kernel.c"
int main(void){ for (int32_t x=0;x<256;x++) printf("%d %d\n", x, pair_law(x)); return 0; }
