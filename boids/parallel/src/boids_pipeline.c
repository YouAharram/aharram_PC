#include "boids_pipeline.h"
#include "boids.h"
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>
#include <stdatomic.h>
#include <unistd.h>   
#include <math.h>
#include <omp.h>
#include <string.h>

static void* worker_func(void* arg) {
    Pipeline* p = (Pipeline*)arg;
    int frame_count = 0; 

    while (atomic_load(&p->running)) {
        if (p->use_grid) {
            
            if (frame_count % 15 == 0) {
                sort_flock(p->flock, p->scratch_flock);
                Boids* sorted_data = p->scratch_flock;
                p->scratch_flock = p->next_flock; 
                p->next_flock = p->flock;         
                p->flock = sorted_data;           
            }

            build_grid(p->flock, p->grid);
            update_boids_grid(p->flock, p->next_flock, p->grid);
        } else {
            update_boids(p->flock, p->next_flock);
        }

        pthread_mutex_lock(&p->mutex);
        Boids* tmp = p->flock;
        p->flock = p->next_flock;
        p->next_flock = tmp;
        pthread_mutex_unlock(&p->mutex);

        frame_count++;
        usleep(16000); 
    }
    return NULL;
}

void pipeline_init(Pipeline* p, int n, int use_grid, unsigned int seed) {
    p->n = n;
    p->use_grid = use_grid;
    p->seed = seed;

    p->flock = malloc(sizeof(Boids));
    p->next_flock = malloc(sizeof(Boids));
    p->scratch_flock = malloc(sizeof(Boids)); 

    p->flock->n = n;
    p->next_flock->n = n;
    p->scratch_flock->n = n;

    size_t size = sizeof(float) * n;
    size = ((size + 63) / 64) * 64;

    p->flock->x  = aligned_alloc(64, size);
    p->flock->y  = aligned_alloc(64, size);
    p->flock->vx = aligned_alloc(64, size);
    p->flock->vy = aligned_alloc(64, size);
    
    p->next_flock->x  = aligned_alloc(64, size);
    p->next_flock->y  = aligned_alloc(64, size);
    p->next_flock->vx = aligned_alloc(64, size);
    p->next_flock->vy = aligned_alloc(64, size);

    p->scratch_flock->x  = aligned_alloc(64, size);
    p->scratch_flock->y  = aligned_alloc(64, size);
    p->scratch_flock->vx = aligned_alloc(64, size);
    p->scratch_flock->vy = aligned_alloc(64, size);

    init_boids(p->flock, n, seed);

    p->grid = aligned_alloc(64, sizeof(Cell) * GRID_ROWS * GRID_COLS);

    atomic_store(&p->running, false);
    pthread_mutex_init(&p->mutex, NULL);
}

void pipeline_start(Pipeline* p) {
    atomic_store(&p->running, true);
    pthread_create(&p->worker_thread, NULL, worker_func, p);
}

void pipeline_stop(Pipeline* p) {
    atomic_store(&p->running, false);
    pthread_join(p->worker_thread, NULL);
}

void pipeline_cleanup(Pipeline* p) {
    if (!p) return;

    free(p->flock->x); free(p->flock->y);
    free(p->flock->vx); free(p->flock->vy);

    free(p->next_flock->x); free(p->next_flock->y);
    free(p->next_flock->vx); free(p->next_flock->vy);

    free(p->flock);
    free(p->next_flock);

    free(p->scratch_flock->x); free(p->scratch_flock->y);
    free(p->scratch_flock->vx); free(p->scratch_flock->vy);
    free(p->scratch_flock);
    free(p->grid);

    pthread_mutex_destroy(&p->mutex);
}

Boids* pipeline_get_latest(Pipeline* p) {
    Boids* result;
    pthread_mutex_lock(&p->mutex);
    result = p->flock;
    pthread_mutex_unlock(&p->mutex);
    return result;
}

BenchmarkResult pipeline_benchmark(Pipeline* p, int steps_per_run, int num_runs) {
    BenchmarkResult res = {0};

    double total_wall = 0.0;
    double total_cpu  = 0.0;
    double min_wall = 1e9, max_wall = 0.0;
    double min_cpu  = 1e9, max_cpu  = 0.0;
    double wall_times[num_runs];

    res.num_threads = omp_get_max_threads();
    omp_sched_t kind;
    int chunk;
    omp_get_schedule(&kind, &chunk);

    switch (kind) {
        case omp_sched_static:
            snprintf(res.schedule, sizeof(res.schedule), "static");
            break;
        case omp_sched_dynamic:
            snprintf(res.schedule, sizeof(res.schedule), "dynamic,%d", chunk);
            break;
        case omp_sched_guided:
            snprintf(res.schedule, sizeof(res.schedule), "guided,%d", chunk);
            break;
        default:
            snprintf(res.schedule, sizeof(res.schedule), "unknown");
    }

    for (int i = 0; i < 5; i++) {
        if (p->use_grid) {
            sort_flock(p->flock, p->scratch_flock);
            
            Boids* sorted_data = p->scratch_flock;
            p->scratch_flock = p->next_flock;
            p->next_flock = p->flock;
            p->flock = sorted_data;

            build_grid(p->flock, p->grid);
            update_boids_grid(p->flock, p->next_flock, p->grid);
        } else {
            update_boids(p->flock, p->next_flock);
        }

        Boids* tmp = p->flock;
        p->flock = p->next_flock;
        p->next_flock = tmp;
    }

    printf("\n--- Avvio Benchmark ---\n");

    for (int r = 0; r < num_runs; r++) {

        double wall_start = omp_get_wtime();
        clock_t cpu_start = clock();

        for (int s = 0; s < steps_per_run; s++) {
            if (p->use_grid) {
                
                if (s % 15 == 0) {
                    sort_flock(p->flock, p->scratch_flock);
                    
                    Boids* sorted_data = p->scratch_flock;
                    p->scratch_flock = p->next_flock;
                    p->next_flock = p->flock;
                    p->flock = sorted_data;
                }

                build_grid(p->flock, p->grid);
                update_boids_grid(p->flock, p->next_flock, p->grid);
            } else {
                update_boids(p->flock, p->next_flock);
            }

            Boids* tmp = p->flock;
            p->flock = p->next_flock;
            p->next_flock = tmp;
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

    return res;
}
