# -------------------------
# Compilatore e Flags
# -------------------------
CC = gcc
CFLAGS = -Wall -Wextra -Iinclude -fopenmp
LDFLAGS = -lraylib -lGL -lm -lpthread -ldl -lrt -lX11 -fopenmp

# Flag ottimizzazione (Aggiunto -ffast-math per il SIMD)
RELEASE_FLAGS = -O3 -march=native -ffast-math
DEBUG_FLAGS = -g

# -------------------------
# Directory
# -------------------------
SRC_DIR = src
TEST_DIR = tests
INC_DIR = include
BIN_DIR = bin
OBJ_DIR = obj

# -------------------------
# Header
# -------------------------
DEPS = $(INC_DIR)/boids.h $(INC_DIR)/boids_pipeline.h

# -------------------------
# MAIN
# -------------------------
SRCS_MAIN = main.c boids_par.c boids_pipeline.c
OBJS_MAIN = $(addprefix $(OBJ_DIR)/, $(SRCS_MAIN:.c=.o))
TARGET_MAIN = $(BIN_DIR)/boids

# -------------------------
# OGGETTI COMUNI PER I TEST
# -------------------------
# Raggruppiamo i core object per non ripeterli
COMMON_OBJS = $(OBJ_DIR)/boids_par.o $(OBJ_DIR)/boids_pipeline.o

# -------------------------
# TESTS SOA
# -------------------------
SRCS_TESTS = tests_soa.c
OBJS_TESTS = $(addprefix $(OBJ_DIR)/, $(SRCS_TESTS:.c=.o))
TARGET_TESTS = $(BIN_DIR)/tests_soa

# -------------------------
# STRONG SCALING
# -------------------------
SRCS_STRONG = strong_scaling.c
OBJS_STRONG = $(addprefix $(OBJ_DIR)/, $(SRCS_STRONG:.c=.o))
TARGET_STRONG = $(BIN_DIR)/strong_scaling

# -------------------------
# WEAK SCALING
# -------------------------
SRCS_WEAK = weak_scaling.c
OBJS_WEAK = $(addprefix $(OBJ_DIR)/, $(SRCS_WEAK:.c=.o))
TARGET_WEAK = $(BIN_DIR)/weak_scaling

# -------------------------
# CHUNK SCALING
# -------------------------
SRCS_CHUNK = chunk_scaling.c
OBJS_CHUNK = $(addprefix $(OBJ_DIR)/, $(SRCS_CHUNK:.c=.o))
TARGET_CHUNK = $(BIN_DIR)/chunk_scaling

# -------------------------
# Regola default
# -------------------------
all: $(BIN_DIR) $(OBJ_DIR) \
     $(TARGET_MAIN) \
     $(TARGET_TESTS) \
     $(TARGET_STRONG) \
     $(TARGET_WEAK) \
     $(TARGET_CHUNK)

# -------------------------
# Creazione cartelle
# -------------------------
$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

# -------------------------
# Compilazione oggetti (SRC)
# -------------------------
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c $(DEPS)
	$(CC) $(CFLAGS) $(RELEASE_FLAGS) -c $< -o $@

# -------------------------
# Compilazione oggetti (TESTS)
# -------------------------
$(OBJ_DIR)/%.o: $(TEST_DIR)/%.c $(DEPS)
	$(CC) $(CFLAGS) $(RELEASE_FLAGS) -c $< -o $@

# -------------------------
# Link main
# -------------------------
$(TARGET_MAIN): $(OBJS_MAIN)
	$(CC) $(OBJS_MAIN) -o $@ $(LDFLAGS)

# -------------------------
# Link tests_soa
# -------------------------
$(TARGET_TESTS): $(OBJS_TESTS) $(COMMON_OBJS)
	$(CC) $^ -o $@ $(LDFLAGS)

# -------------------------
# Link strong_scaling
# -------------------------
$(TARGET_STRONG): $(OBJS_STRONG) $(COMMON_OBJS)
	$(CC) $^ -o $@ $(LDFLAGS)

# -------------------------
# Link weak_scaling
# -------------------------
$(TARGET_WEAK): $(OBJS_WEAK) $(COMMON_OBJS)
	$(CC) $^ -o $@ $(LDFLAGS)

# -------------------------
# Link chunk_scaling
# -------------------------
$(TARGET_CHUNK): $(OBJS_CHUNK) $(COMMON_OBJS)
	$(CC) $^ -o $@ $(LDFLAGS)

# -------------------------
# Build debug
# -------------------------
debug: RELEASE_FLAGS = $(DEBUG_FLAGS)
debug: all

# -------------------------
# Pulizia
# -------------------------
clean:
	rm -rf $(BIN_DIR)/* $(OBJ_DIR)/*

.PHONY: all clean debug
