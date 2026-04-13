#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <omp.h>
#include "boids.h"
#include <time.h>
#include "../include/benchmark.h"

BenchmarkResultSeq benchmark_sequential(
    Boid* flock,
    Boid* next_flock,
    int n,
    int use_grid,
    Cell (*grid)[GRID_COLS],
    int steps_per_run,
    int num_runs
) {
    BenchmarkResultSeq res = {0};

    if (num_runs < 2) {
        fprintf(stderr, "Errore: num_runs deve essere >= 2\n");
        return res;
    }

    double total_wall = 0.0;
    double total_cpu  = 0.0;

    double min_wall = 1e9, max_wall = 0.0;
    double min_cpu  = 1e9, max_cpu  = 0.0;

    double* wall_times = malloc(sizeof(double) * (num_runs - 1));
    if (!wall_times) {
        perror("malloc");
        return res;
    }

    // Warm-up
    for (int i = 0; i < 5; i++) {
        if (use_grid) {
            build_grid(flock, n, grid);
            update_boids_grid_sequential(flock, next_flock, n, grid);
        } else {
            update_boids_sequential(flock, next_flock, n);
        }

        Boid* tmp = flock;
        flock = next_flock;
        next_flock = tmp;
    }

    // Benchmark
    for (int r = 0; r < num_runs; r++) {
        double wall_start = omp_get_wtime();
        clock_t cpu_start = clock();

        for (int s = 0; s < steps_per_run; s++) {
            if (use_grid) {
                build_grid(flock, n, grid);
                update_boids_grid_sequential(flock, next_flock, n, grid);
            } else {
                update_boids_sequential(flock, next_flock, n);
            }

            Boid* tmp = flock;
            flock = next_flock;
            next_flock = tmp;
        }

        double wall_time = omp_get_wtime() - wall_start;
        double cpu_time  = (double)(clock() - cpu_start) / CLOCKS_PER_SEC;

        if (r > 0) {
            total_wall += wall_time;
            total_cpu  += cpu_time;
            wall_times[r - 1] = wall_time;
            if (wall_time < min_wall) min_wall = wall_time;
            if (wall_time > max_wall) max_wall = wall_time;
            if (cpu_time < min_cpu) min_cpu = cpu_time;
            if (cpu_time > max_cpu) max_cpu = cpu_time;
        }
    }

    int effective_runs = num_runs - 1;

    res.mean_wall = total_wall / effective_runs;
    res.mean_cpu  = total_cpu  / effective_runs;
    res.min_wall  = min_wall;
    res.max_wall  = max_wall;
    res.min_cpu   = min_cpu;
    res.max_cpu   = max_cpu;

    double variance = 0.0;
    for (int i = 0; i < effective_runs; i++) {
        double diff = wall_times[i] - res.mean_wall;
        variance += diff * diff;
    }
    res.std_wall = sqrt(variance / effective_runs);

    free(wall_times);

    return res;
}
