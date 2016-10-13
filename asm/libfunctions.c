#include <msp430.h>

void main (void) {
    const char *s1 = "hello world !";
    const char *s2 = "how are you today";

    volatile char buf[32];

    volatile short x;
    volatile short y;
    volatile short z;

    x = strcmp(s1, buf);

    y = 17;
    z = x * y;

    while(1){}
}
