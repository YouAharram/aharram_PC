#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "../include/boids_pipeline.h"

int main() {
	
    int BOIDS_LIST[] = {1000, 3000, 5000, 7000, 10000, 15000, 20000};
    const char* SCHEDULES[] = {"static", "dynamic,32", "guided"};
    int THREADS_LIST[] = {2, 4, 8, 16, 20, 32};
    unsigned int SEED = 42;
    FILE* f = fopen("tests_results/benchmark_results.csv", "w");
    if (!f) {
        perror("Errore apertura file");
        return 1;
    }

    fprintf(f, "type,threads,boids,schedule,mean_wall,min_wall,max_wall,std_wall,mean_cpu,min_cpu,max_cpu\n");

    for (size_t ti = 0; ti < sizeof(THREADS_LIST)/sizeof(int); ti++) {
        int t = THREADS_LIST[ti];
        omp_set_num_threads(t);

        for (size_t bi = 0; bi < sizeof(BOIDS_LIST)/sizeof(int); bi++) {
            int b = BOIDS_LIST[bi];

            for (size_t si = 0; si < sizeof(SCHEDULES)/sizeof(char*); si++) {

                const char* sched = SCHEDULES[si];

                if (strncmp(sched, "static", 6) == 0) {
                    omp_set_schedule(omp_sched_static, 0);
                }
                else if (strncmp(sched, "dynamic", 7) == 0) {
                    int chunk = 32;
                    sscanf(sched, "dynamic,%d", &chunk);
                    omp_set_schedule(omp_sched_dynamic, chunk);
                }
                else if (strncmp(sched, "guided", 6) == 0) {
                    int chunk = 1;
                    sscanf(sched, "guided,%d", &chunk);
                    omp_set_schedule(omp_sched_guided, chunk);
                }

                printf("Running: threads=%d boids=%d schedule=%s\n", t, b, sched);

                Pipeline p;
                pipeline_init(&p, b, 1, SEED);

                BenchmarkResult res = pipeline_benchmark(&p, 1000, 10);

                pipeline_cleanup(&p);

                fprintf(f, "SoA,%d,%d,%s,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
                        res.num_threads, b, res.schedule,
                        res.mean_wall, res.min_wall, res.max_wall, res.std_wall,
                        res.mean_cpu, res.min_cpu, res.max_cpu);

                fflush(f);
            }
        }
    }
    fclose(f);
    printf("Benchmark completato.\n");
    return 0;
}
