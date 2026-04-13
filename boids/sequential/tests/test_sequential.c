#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "boids.h"
#include "../include/benchmark.h"

int main() {

    // Lista di boids (stessi valori della versione parallela)
    int BOIDS_LIST[] = {1000, 3000, 5000, 7000, 10000, 15000, 20000};

    // Non servono schedule o threads per la versione sequenziale
    const int use_grid = 0;      // 0 = brute-force, 1 = grid
    const unsigned int SEED = 42;

    FILE* f = fopen("tests_results/benchmark_results_seq.csv", "w");
    if (!f) {
        perror("Errore apertura file");
        return 1;
    }

    fprintf(f, "type,threads,boids,schedule,mean_wall,min_wall,max_wall,std_wall,mean_cpu,min_cpu,max_cpu\n");

    for (size_t bi = 0; bi < sizeof(BOIDS_LIST)/sizeof(int); bi++) {
        int b = BOIDS_LIST[bi];

        printf("\n==== Benchmark sequenziale: %d boids ====\n", b);

        // Inizializzazione boids
        Boid* flock = malloc(sizeof(Boid) * b);
        Boid* next_flock = malloc(sizeof(Boid) * b);
        if (!flock || !next_flock) {
            perror("malloc");
            return 1;
        }

        init_boids(flock, b, SEED);

        Cell grid[GRID_ROWS][GRID_COLS]; // se si usa la griglia

        BenchmarkResultSeq res = benchmark_sequential(
            flock,
            next_flock,
            b,
            use_grid,
            grid,
            1000, // steps_per_run
            10    // num_runs
        );

        // Scrittura CSV (threads = 1, schedule = "seq")
        fprintf(f, "Seq,1,%d,seq,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
                b,
                res.mean_wall, res.min_wall, res.max_wall, res.std_wall,
                res.mean_cpu, res.min_cpu, res.max_cpu);

        fflush(f);

        free(flock);
        free(next_flock);
    }

    fclose(f);

    printf("\nBenchmark sequenziale completato.\n");
    return 0;
}
