CC = gcc

export LDFLAGS = -lpthread -lrt -ldl
export CFLAGS = -O2 -D_GNU_SOURCE -fno-strict-aliasing -Wall -Wextra \
	-Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations \
	-Wdeclaration-after-statement -Wno-missing-field-initializers \
	-Wno-unused-parameter
INCLUDES = -I../ncrx

debug debug32: CFLAGS += -O0 -gdwarf-4 -fno-omit-frame-pointer \
	-fstack-protector-all -fsanitize=address -fsanitize=undefined
debug debug32: LDFLAGS := -lasan -lubsan $(LDFLAGS)

32bit: CFLAGS += -m32
32bit: LDFLAGS += -m32

disasm: CFLAGS += -fverbose-asm

binary = netconsd
lib = ../ncrx/libncrx.o
obj = threads.o listener.o worker.o output.o main.o
asm = $(obj:.o=.s)

all: $(binary) mods
32bit: $(binary) mods

debug: all
debug32: 32bit
disasm: $(asm)

-include $(obj:.o=.d)

$(binary): $(lib) $(obj)
	$(CC) $(LDFLAGS) $(lib) $(obj) -o $@

%.o: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) -c -o $@
	$(CC) -MM $< $(INCLUDES) > $(@:.o=.d)

%.s: %.c
	$(CC) $< $(CFLAGS) $(INCLUDES) -c -S -o $@

$(lib):
	$(MAKE) -e -C ../ncrx

mods:
	$(MAKE) -e -C modules

utils:
	$(MAKE) -e -C util

clean:
	rm -f netconsd *.o *.d *.s
	rm -f modules/*.o modules/*.so
	rm -f ../ncrx/*.o ../ncrx/*.d
	rm -f util/netconsblaster
