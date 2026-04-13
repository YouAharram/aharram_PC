#ifndef BENCHMARK_H
#define BENCHMARK_H

#include "boids.h"

// Struttura per risultati benchmark sequenziale
typedef struct {
    double mean_wall, min_wall, max_wall, std_wall;
    double mean_cpu, min_cpu, max_cpu;
} BenchmarkResultSeq;

// Funzione di benchmark sequenziale
BenchmarkResultSeq benchmark_sequential(
    Boid* flock,
    Boid* next_flock,
    int n,
    int use_grid,
    Cell (*grid)[GRID_COLS],
    int steps_per_run,
    int num_runs
);

#endif
