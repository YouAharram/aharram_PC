#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "../include/boids_pipeline.h"

void set_schedule(const char* sched) {
    if (strncmp(sched, "static", 6) == 0) {
        omp_set_schedule(omp_sched_static, 0);
    } else if (strncmp(sched, "dynamic", 7) == 0) {
        int chunk = 32;
        sscanf(sched, "dynamic,%d", &chunk);
        omp_set_schedule(omp_sched_dynamic, chunk);
    } else if (strncmp(sched, "guided", 6) == 0) {
        int chunk = 1;
        sscanf(sched, "guided,%d", &chunk);
        omp_set_schedule(omp_sched_guided, chunk);
    }
}

int main() {
    int CHUNK_LIST[] = {1, 2, 4, 8, 16, 32, 64, 128};
    int THREADS = 20;                
    int BOIDS = 10000;              
    const char* POLICY = "dynamic";
    unsigned int SEED = 42;

    FILE* f = fopen("tests_results/chunk_scaling_results_soa.csv", "w");
    if (!f) {
        perror("Errore apertura file");
        return 1;
    }

    fprintf(f, "threads,boids,policy,chunk,mean_wall,min_wall,max_wall,std_wall,mean_cpu,min_cpu,max_cpu\n");
    fflush(f);

    printf("\n=== CHUNK SIZE SCALING SoA (%s) ===\n", POLICY);

    omp_set_num_threads(THREADS);

    for (size_t ci = 0; ci < sizeof(CHUNK_LIST)/sizeof(int); ci++) {
        int chunk = CHUNK_LIST[ci];
        char sched_str[32];
        snprintf(sched_str, sizeof(sched_str), "%s,%d", POLICY, chunk);
        set_schedule(sched_str);

        Pipeline p;
        pipeline_init(&p, BOIDS, 1, SEED); // 1 = SoA
        BenchmarkResult res = pipeline_benchmark(&p, 1000, 5);
        pipeline_cleanup(&p);

        fprintf(f, "%d,%d,%s,%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
                THREADS, BOIDS, POLICY, chunk,
                res.mean_wall, res.min_wall, res.max_wall, res.std_wall,
                res.mean_cpu, res.min_cpu, res.max_cpu);

        fflush(f);
        printf("chunk=%3d | time=%.4f s\n", chunk, res.mean_wall);
    }
    fclose(f);
    printf("\nTest chunk size SoA completato. File: chunk_scaling_results_soa.csv\n");
    return 0;
}
