#include "../include/boids.h"

// RNG deterministico
static inline float rand_float_seq(unsigned int* state, float min, float max) {
    *state = 1664525 * (*state) + 1013904223;
    float t = (float)(*state & 0xFFFFFF) / (float)0x1000000;
    return min + t * (max - min);
}

// Inizializzazione boids
void init_boids(Boid* flock, int n, unsigned int seed) {
    for (int i = 0; i < n; i++) {
        unsigned int s = seed + i;
        flock[i].x  = rand_float_seq(&s, 100.0f, SCREEN_WIDTH - 100.0f);
        flock[i].y  = rand_float_seq(&s, 100.0f, SCREEN_HEIGHT - 100.0f);
        flock[i].vx = rand_float_seq(&s, -2.0f, 2.0f);
        flock[i].vy = rand_float_seq(&s, -2.0f, 2.0f);
    }
}
