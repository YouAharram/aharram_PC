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
    int THREADS_LIST[] = {2, 4, 8, 14, 16, 20, 32};
    int BOIDS_PER_THREAD = 1000;
    const char* SCHEDULE = "dynamic,32"; 
    unsigned int SEED = 42;

    FILE* f = fopen("tests_results/weak_scaling_results.csv", "w");
    if (!f) { perror("Errore apertura file"); return 1; }
    fprintf(f, "threads,boids,schedule,mean_wall,min_wall,max_wall,std_wall,mean_cpu,min_cpu,max_cpu\n");
    fflush(f);

    printf("\n=== WEAK SCALING ===\n");
    for (size_t ti = 0; ti < sizeof(THREADS_LIST)/sizeof(int); ti++) {
        int t = THREADS_LIST[ti];
        omp_set_num_threads(t);
        set_schedule(SCHEDULE);

        int boids = BOIDS_PER_THREAD * t;

        Pipeline p;
        pipeline_init(&p, boids, 1, SEED);
        BenchmarkResult res = pipeline_benchmark(&p, 1000, 5);
        pipeline_cleanup(&p);

        fprintf(f, "%d,%d,%s,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
                t, boids, SCHEDULE,
                res.mean_wall, res.min_wall, res.max_wall, res.std_wall,
                res.mean_cpu, res.min_cpu, res.max_cpu);
        
	printf("%d,%d,%s,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
                t, boids, SCHEDULE,
                res.mean_wall, res.min_wall, res.max_wall, res.std_wall,
                res.mean_cpu, res.min_cpu, res.max_cpu);

	fflush(f);

        printf("T=%d time=%.4f s | boids=%d | sched=%s\n", t, res.mean_wall, boids, SCHEDULE);
    }

    fclose(f);
    printf("\nWeak scaling completato. Risultati salvati in weak_scaling_results.csv\n");
    return 0;
}
