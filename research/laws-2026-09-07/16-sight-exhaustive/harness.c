/* 16-sight-exhaustive: dump the AUTHORED C kernel and its own spec() for all
 * 256 inputs, so the Python port can be diffed against the kernel itself
 * (not just against a Python transcription of the spec).
 *
 * The authored file is included verbatim with its main() renamed, so both
 * sight() and the file-static spec() are visible here unchanged.
 *
 *   cc -O2 -o sight_table harness.c && ./sight_table > c_table.txt
 *   cc -O1 -fsanitize=undefined -o sight_table_ubsan harness.c && ./sight_table_ubsan
 */
#define main sight_authored_selfcheck_main
#include "/Users/kanchetidevieswar/neo/fluidfix/docs/laws/sight.c"
#undef main

int main(void)
{
    for (int32_t x = 0; x < 256; x++)
        printf("%d %d %d\n", x, sight(x), spec(x));
    /* also: does the C kernel add exactly the byte's bit 7 on non-pointing
       inputs?  (the penalty term is gate & (x >> 7)) */
    long pen_bad = 0;
    for (int32_t x = 0; x < 128; x++)
        if (!(x & 7) && sight(x | 128) != sight(x) + 1) pen_bad++;
    fprintf(stderr, "C kernel: non-pointing inputs where UBIQ != +1: %ld\n", pen_bad);
    return 0;
}
