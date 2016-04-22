CC = gcc
CCC = g++

CFLAGS = -O2 -D_GNU_SOURCE -fPIC -fno-strict-aliasing -Wall -Wextra \
	-Wno-unused-function -Wno-unused-parameter \
	-Wno-missing-field-initializers
CCFLAGS = -std=c++17 $(CFLAGS)
INCLUDES = -I../../ncrx -I ../include

mods = printer.so logger.so

all: $(mods)

%.so: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) -c -o $(<:.c=.o)
	$(CC) $(<:.c=.o) -shared -o $@

%.so: %.cc
	$(CCC) $< $(CCFLAGS) $(INCLUDES) -c -o $(<:.cc=.o)
	$(CCC) $(<:.cc=.o) -shared -static-libstdc++ -static-libgcc -o $@

clean:
	rm -f *.o *.so
