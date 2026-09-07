#include <stdio.h>
#include "scale.h"

int main(void)
{
	if (scale(5) != 25) {
		printf("condition false: scale(5) == 25\n");
		printf("test failed: ScaleTest\n");
		return 1;
	}
	printf("All tests passed!\n");
	return 0;
}
