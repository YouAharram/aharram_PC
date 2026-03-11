#include "../include/boids.h"
#include <math.h>

// Parametri fisici (calibrabili)
static const float visual_range = 40.0f;
//static const float protected_range = 8.0f;
static const float visual_range_sq = 1600.0f;    // 40 * 40
static const float protected_range_sq = 64.0f;  // 8 * 8
static const float centering_factor = 0.0005f;
static const float avoidfactor = 0.05f;
static const float matching_factor = 0.05f;
static const float maxspeed = 3.0f;
static const float minspeed = 2.0f;
static const float turnfactor = 0.2f;

void update_boids_sequential(Boid* flock, int n) {
    for (int i = 0; i < n; i++) {
        // 1. Inizializza accumulatori
        float xpos_avg = 0, ypos_avg = 0;
        float xvel_avg = 0, yvel_avg = 0;
        int neighboring_boids = 0;
        float close_dx = 0, close_dy = 0;

        for (int j = 0; j < n; j++) {
            if (i == j) continue; // Non confrontarti con te stesso

            float dx = flock[i].x - flock[j].x;
            float dy = flock[i].y - flock[j].y;

            // Controllo rapido nel range visivo (bounding box)
            if (fabsf(dx) < visual_range && fabsf(dy) < visual_range) {
                float squared_distance = dx*dx + dy*dy;

                // Regola 1: Separazione (Protected Range)
                if (squared_distance < protected_range_sq) {
                    close_dx += flock[i].x - flock[j].x;
                    close_dy += flock[i].y - flock[j].y;
                }
                // Regole 2 e 3: Allineamento e Coesione (Visual Range)
                else if (squared_distance < visual_range_sq) {
                    xpos_avg += flock[j].x;
                    ypos_avg += flock[j].y;
                    xvel_avg += flock[j].vx;
                    yvel_avg += flock[j].vy;
                    neighboring_boids++;
                }
            }
        }

        // Applicazione medie se ci sono vicini
        if (neighboring_boids > 0) {
            xpos_avg /= neighboring_boids;
            ypos_avg /= neighboring_boids;
            xvel_avg /= neighboring_boids;
            yvel_avg /= neighboring_boids;

            flock[i].vx += (xpos_avg - flock[i].x) * centering_factor + 
                           (xvel_avg - flock[i].vx) * matching_factor;
            flock[i].vy += (ypos_avg - flock[i].y) * centering_factor + 
                           (yvel_avg - flock[i].vy) * matching_factor;
        }

        // Aggiunta forza di evitamento (Separazione)
        flock[i].vx += (close_dx * avoidfactor);
        flock[i].vy += (close_dy * avoidfactor);

        // --- GESTIONE BORDI (Box) ---
        if (flock[i].y < 50)  flock[i].vy += turnfactor;    // Top
        if (flock[i].y > SCREEN_HEIGHT - 50) flock[i].vy -= turnfactor; // Bottom
        if (flock[i].x < 50)  flock[i].vx += turnfactor;    // Left
        if (flock[i].x > SCREEN_WIDTH - 50)  flock[i].vx -= turnfactor; // Right

        // --- LIMITAZIONE VELOCITÀ ---
        float speed = sqrtf(flock[i].vx * flock[i].vx + flock[i].vy * flock[i].vy);
        if (speed < minspeed) {
            flock[i].vx = (flock[i].vx / speed) * minspeed;
            flock[i].vy = (flock[i].vy / speed) * minspeed;
        }
        if (speed > maxspeed) {
            flock[i].vx = (flock[i].vx / speed) * maxspeed;
            flock[i].vy = (flock[i].vy / speed) * maxspeed;
        }

        // --- AGGIORNAMENTO POSIZIONE ---
        flock[i].x += flock[i].vx;
        flock[i].y += flock[i].vy;
    }
}
