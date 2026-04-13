#ifndef BOIDS_PIPELINE_H
#define BOIDS_PIPELINE_H

#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include "boids.h"

typedef struct {
    int n;               
    bool use_grid;       
    unsigned int seed;   
    Boids* scratch_flock;    
    Boids* flock;        
    Boids* next_flock;   
    Cell (*grid)[GRID_COLS]; 
    atomic_bool running;      
    pthread_t worker_thread;  
    pthread_mutex_t mutex;    
} Pipeline;

typedef struct {
    double mean_wall;
    double min_wall;
    double max_wall;
    double std_wall;
    double mean_cpu;
    double min_cpu;
    double max_cpu;
    int num_threads;
    char schedule[32];
} BenchmarkResult;

void pipeline_init(Pipeline* p, int n, int use_grid, unsigned int seed);
void pipeline_start(Pipeline* p);
void pipeline_stop(Pipeline* p);
void pipeline_cleanup(Pipeline* p);

Boids* pipeline_get_latest(Pipeline* p);
BenchmarkResult pipeline_benchmark(Pipeline* p, int steps_per_run, int num_runs);

#endif
