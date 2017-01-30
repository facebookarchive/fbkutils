CC = gcc
CCC = g++

override CFLAGS += -fPIC
INCLUDES = -I../../ncrx -I../include

# Filter out warnings not cpp-applicable that g++ complains about
CCFLAGS := -std=c++11 $(filter-out -Wstrict-prototypes -Wmissing-prototypes \
		-Wdeclaration-after-statement,$(CFLAGS))

mods = printer.so logger.so

all: $(mods)

%.so: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) $(LDFLAGS) -c -o $(<:.c=.o)
	$(CC) $(<:.c=.o) $(LDFLAGS) -shared -o $@

%.so: %.cc
	$(CCC) $< $(CCFLAGS) $(INCLUDES) $(LDFLAGS) -c -o $(<:.cc=.o)
	$(CCC) $(<:.cc=.o) $(LDFLAGS) -shared -static-libstdc++ -static-libgcc \
			-o $@

clean:
	rm -f *.o *.so
