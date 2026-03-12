# Compilatore e Flag
CC = gcc
# Aggiungiamo -D_DEFAULT_SOURCE per compatibilità con alcune funzioni di sistema se necessario
CFLAGS = -Wall -Wextra -Iinclude -fopenmp
LDFLAGS = -lraylib -lGL -lm -lpthread -ldl -lrt -lX11 -fopenmp

# Flag per l'ottimizzazione
RELEASE_FLAGS = -O3 -march=native
DEBUG_FLAGS = -g

# Directory
SRC_DIR = src
INC_DIR = include
BIN_DIR = bin

# Header principale (se cambia questo, ricompila tutto)
DEPS = $(INC_DIR)/boids.h

# File Sorgente
SRCS_SEQ = $(SRC_DIR)/main.c $(SRC_DIR)/boids_seq.c
# Qui potrai aggiungere in futuro: SRCS_OMP = $(SRC_DIR)/main_omp.c $(SRC_DIR)/boids_omp.c

# Target
TARGET_SEQ = $(BIN_DIR)/boids_seq

# Regola di default
all: $(BIN_DIR) $(TARGET_SEQ)

# Creazione cartella bin
$(BIN_DIR):
	mkdir -p $(BIN_DIR)

# Compilazione Sequenziale
# Aggiungiamo $(DEPS) alle dipendenze così se modifichi l'header il make se ne accorge
$(TARGET_SEQ): $(SRCS_SEQ) $(DEPS)
	$(CC) $(CFLAGS) $(RELEASE_FLAGS) $(SRCS_SEQ) -o $@ $(LDFLAGS)

# Target per il Debug
debug: RELEASE_FLAGS = $(DEBUG_FLAGS)
debug: all

# Esempio di come potrai aggiungere la versione OpenMP tra poco
# omp: $(BIN_DIR) $(BIN_DIR)/boids_omp
# $(BIN_DIR)/boids_omp: $(SRC_DIR)/main.c $(SRC_DIR)/boids_omp.c $(DEPS)
# 	$(CC) $(CFLAGS) $(RELEASE_FLAGS) $^ -o $@ $(LDFLAGS)

clean:
	rm -rf $(BIN_DIR)/* $(SRC_DIR)/*.o

.PHONY: all clean debug
