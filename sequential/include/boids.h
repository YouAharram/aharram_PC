#ifndef BOIDS_H
#define BOIDS_H

#include <omp.h> // Utile includerlo qui per avere sempre il timer disponibile

// --- 1. COSTANTI DI SIMULAZIONE ---
#define SCREEN_WIDTH 1380
#define SCREEN_HEIGHT 820
#define CELL_SIZE 40
#define GRID_COLS (SCREEN_WIDTH / CELL_SIZE + 1)
#define GRID_ROWS (SCREEN_HEIGHT / CELL_SIZE + 1)
#define MAX_BOIDS_PER_CELL 100 

// --- 2. STRUTTURE DATI ---

// Struttura per il singolo Boid (AoS)
typedef struct {
    float x, y;
    float vx, vy;
} Boid;

// Struttura per la cella della griglia spaziale
typedef struct {
    int count;
    int boid_indices[MAX_BOIDS_PER_CELL];
} Cell;

// --- 3. PROTOTIPI DELLE FUNZIONI ---

// Inizializzazione
void init_boids(Boid* flock, int n);

// Versione Brute Force (O(n^2))
void update_boids_sequential(Boid* in, Boid* out, int n);

// Versione con Griglia (O(n))
// Passiamo la griglia come puntatore per evitare di occupare troppo stack
void build_grid(Boid* flock, int n, Cell (*grid)[GRID_COLS]);
void update_boids_grid_sequential(Boid* in, Boid* out, int n, Cell (*grid)[GRID_COLS]);

#endif
