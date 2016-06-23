CC = gcc

LDFLAGS = -lpthread -lrt -ldl
export CFLAGS = -O2 -D_GNU_SOURCE -fno-strict-aliasing -Wall -Wextra \
	-Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations \
	-Wdeclaration-after-statement -Wno-missing-field-initializers \
	-Wno-unused-function -Wno-unused-parameter
INCLUDES = -I../ncrx

debug: CFLAGS += -Og -gdwarf-4 -fno-omit-frame-pointer -fstack-protector-all \
	-fsanitize=address -fsanitize=undefined
debug: LDFLAGS := -lasan -lubsan $(LDFLAGS)

netconsblaster:
	$(CC) $(LDFLAGS) $(CFLAGS) util/netconsblaster.c -o util/netconsblaster

binary = netconsd
lib = ../ncrx/libncrx.o
obj = threads.o listener.o worker.o output.o main.o

all: $(binary)
debug: all

-include $(obj:.o=.d)

$(binary): $(lib) $(obj)
	$(CC) $(LDFLAGS) $(lib) $(obj) -o $@

$(lib):
	$(MAKE) -e -C ../ncrx -f ../ncrx/Makefile

%.o: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) -c -o $@
	$(CC) -MM $(CFLAGS) $< > $(@:.o=.d)

clean:
	rm -f netconsd *.o *.d
