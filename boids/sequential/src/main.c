#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#include "raylib.h"
#include "../include/boids.h"
#include "../include/benchmark.h"

int main(int argc, char** argv) {

    int num_boids = 1000;
    int benchmark_mode = 0;
    int use_grid = 0;
    unsigned int seed = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--bench") == 0) {
            benchmark_mode = 1;
            if (i + 1 < argc && argv[i+1][0] != '-')
                num_boids = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--grid") == 0) {
            use_grid = 1;
        } else if (strcmp(argv[i], "--seed") == 0) {
            if (i + 1 < argc)
                seed = (unsigned int)atoi(argv[++i]);
        } else if (argv[i][0] != '-') {
            num_boids = atoi(argv[i]);
        }
    }

    Boid* flock = malloc(sizeof(Boid) * num_boids);
    Boid* next_flock = malloc(sizeof(Boid) * num_boids);
    Cell (*grid)[GRID_COLS] = malloc(sizeof(Cell) * GRID_ROWS * GRID_COLS);

    if (!flock || !next_flock || !grid) {
        fprintf(stderr, "Errore allocazione memoria\n");
        return 1;
    }

    // Inizializzazione boids
    init_boids(flock, num_boids, seed);
    memcpy(next_flock, flock, sizeof(Boid) * num_boids);

    if (benchmark_mode) {
        // Benchmark sequenziale
        benchmark_sequential(flock, next_flock,
                          num_boids, use_grid,
                          grid, 1000, 10);
    } else {
        InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "Boids - Sequenziale");
        SetTargetFPS(60);

        while (!WindowShouldClose()) {
            if (use_grid) {
                build_grid(flock, num_boids, grid);
                update_boids_grid_sequential(flock, next_flock, num_boids, grid);
            } else {
                update_boids_sequential(flock, next_flock, num_boids);
            }

            Boid* tmp = flock;
            flock = next_flock;
            next_flock = tmp;

            BeginDrawing();
                ClearBackground(BLACK);
                for (int i = 0; i < num_boids; i++) {
                    DrawCircleV((Vector2){flock[i].x, flock[i].y}, 2.0f, RAYWHITE);
                }
                DrawFPS(10, 10);
                DrawText(TextFormat("Boids: %d | Grid: %s",
                         num_boids, use_grid ? "ON" : "OFF"),
                         10, 40, 20, GREEN);
            EndDrawing();
        }

        CloseWindow();
    }

    free(flock);
    free(next_flock);
    free(grid);

    return 0;
}
