binary = bsdacctd
obj = bsdacctd.o
all: $(binary)

$(binary): $(obj)
	gcc $(obj) -o $@

%.o: %.c
	gcc -D_GNU_SOURCE -O2 -Wall -Wextra -fno-strict-aliasing $< -c -o $@

clean:
	rm -f $(obj) $(binary)
