CC = gcc
CFLAGS = -Wall -Wextra -O2 -std=c99
TARGET = text_rank

$(TARGET): text_rank.c
	$(CC) $(CFLAGS) -o $(TARGET) text_rank.c -lm

clean:
	rm -f $(TARGET)
