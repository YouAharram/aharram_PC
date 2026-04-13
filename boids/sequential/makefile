# Compilatore e flags
CC = gcc
CFLAGS = -Wall -Wextra -O3 -march=native -Iinclude -fopenmp
LDFLAGS = -lraylib -lGL -lm -lpthread -ldl -lrt -lX11 -fopenmp

# Directory
SRC_DIR = src
BIN_DIR = bin
TEST_DIR = tests

# File sorgenti
SRC_MAIN_SEQ = $(SRC_DIR)/main.c $(SRC_DIR)/boids_seq.c $(SRC_DIR)/boids_init.c $(SRC_DIR)/benchmark.c
SRC_TEST_SEQ = $(TEST_DIR)/test_sequential.c $(SRC_DIR)/boids_seq.c $(SRC_DIR)/boids_init.c $(SRC_DIR)/benchmark.c

# Output
BIN_MAIN_SEQ = $(BIN_DIR)/boids_seq
BIN_TEST_SEQ = $(BIN_DIR)/test_sequential

# Default target
all: $(BIN_MAIN_SEQ) $(BIN_TEST_SEQ)

# Compila main sequenziale
$(BIN_MAIN_SEQ): $(SRC_MAIN_SEQ)
	@mkdir -p $(BIN_DIR)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

# Compila test sequenziale
$(BIN_TEST_SEQ): $(SRC_TEST_SEQ)
	@mkdir -p $(BIN_DIR)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

# Pulizia
clean:
	rm -rf $(BIN_DIR)/*.o $(BIN_DIR)/boids_seq $(BIN_DIR)/test_sequential

.PHONY: all clean
