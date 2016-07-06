CC = gcc

LDFLAGS = -lpthread -lrt -ldl
export CFLAGS = -O2 -D_GNU_SOURCE -fno-strict-aliasing -Wall -Wextra \
	-Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations \
	-Wdeclaration-after-statement -Wno-missing-field-initializers \
	-Wno-unused-function -Wno-unused-parameter
INCLUDES = -I../ncrx

debug debug32: CFLAGS += -Og -gdwarf-4 -fno-omit-frame-pointer \
	-fstack-protector-all -fsanitize=address -fsanitize=undefined
debug debug32: LDFLAGS := -lasan -lubsan $(LDFLAGS)

32bit: CFLAGS += -m32
32bit: LDFLAGS += -m32

disasm: CFLAGS += -fverbose-asm

binary = netconsd
lib = ../ncrx/libncrx.o
obj = threads.o listener.o worker.o output.o main.o
asm = $(obj:.o=.s)

all: $(binary)
32bit: $(binary)

debug: all
debug32: 32bit
disasm: $(asm)

-include $(obj:.o=.d)

$(binary): $(lib) $(obj)
	$(CC) $(LDFLAGS) $(lib) $(obj) -o $@

$(lib):
	$(MAKE) -e -C ../ncrx -f ../ncrx/Makefile

%.o: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) -c -o $@
	$(CC) -MM $< > $(@:.o=.d)

%.s: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) -c -S -o $@

netconsblaster:
	$(CC) $(LDFLAGS) $(CFLAGS) util/netconsblaster.c -o util/netconsblaster

clean:
	rm -f netconsd *.o *.d *.s
	rm -f ../ncrx/libncrx.o
