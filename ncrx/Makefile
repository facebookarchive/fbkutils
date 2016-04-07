CC = gcc

CFLAGS = -O2 -D_GNU_SOURCE -fno-strict-aliasing -Wall -Wextra \
	-Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations \
	-Wdeclaration-after-statement -Wno-missing-field-initializers \
	-Wno-unused-function -Wno-unused-parameter

obj = libncrx.o

all: $(obj)

%.o: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) -c -o $@

clean:
	rm -f *.o
