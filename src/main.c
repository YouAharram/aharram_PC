#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "raylib.h"
#include "../include/boids.h"

// Funzione di utilità per inizializzare i boid con valori casuali
void init_boids(Boid* flock, int n) {
    for (int i = 0; i < n; i++) {
        // Posizione casuale all'interno dello schermo (con un po' di margine)
        flock[i].x = (float)(GetRandomValue(100, SCREEN_WIDTH - 100));
        flock[i].y = (float)(GetRandomValue(100, SCREEN_HEIGHT - 100));
        
        // Velocità casuale tra -2.0 e 2.0
        flock[i].vx = (float)GetRandomValue(-200, 200) / 100.0f;
        flock[i].vy = (float)GetRandomValue(-200, 200) / 100.0f;
    }
}

int main(void) {
    // Numero di boid per la versione sequenziale (iniziamo con 1000)
    const int num_boids = 1000;
    Boid *flock = malloc(sizeof(Boid) * num_boids);

    // Inizializzazione Raylib
    InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "Boids Simulation - Sequential");
    SetTargetFPS(60); // Limita a 60 FPS per una visualizzazione fluida

    // Seme per i numeri casuali e init boids
    srand(time(NULL));
    init_boids(flock, num_boids);

    // Loop principale della finestra
    while (!WindowShouldClose()) {
        
        // 1. UPDATE: Calcola la nuova fisica (Sequenziale)
        // Misureremo il tempo di questa funzione per i tuoi grafici futuri
        double startTime = GetTime();
        update_boids_sequential(flock, num_boids);
        double updateTime = GetTime() - startTime;

        // 2. DRAW: Disegna i boid sullo schermo
        BeginDrawing();
            ClearBackground(BLACK); // Sfondo nero per vedere bene i boid

            for (int i = 0; i < num_boids; i++) {
                // Disegniamo un piccolo cerchio per ogni boid
                DrawCircleV((Vector2){flock[i].x, flock[i].y}, 2.0f, RAYWHITE);
                
                // Opzionale: Disegna una piccola linea per mostrare la direzione (velocità)
                DrawLineV((Vector2){flock[i].x, flock[i].y}, 
                          (Vector2){flock[i].x + flock[i].vx*3, flock[i].y + flock[i].vy*3}, 
                          SKYBLUE);
            }

            // Mostra statistiche a schermo
            DrawText(TextFormat("Boids: %i", num_boids), 10, 10, 20, GREEN);
            DrawText(TextFormat("Update Time: %.3f ms", updateTime * 1000), 10, 35, 20, GREEN);
            DrawFPS(10, 60);

        EndDrawing();
    }

    // Cleanup
    free(flock);
    CloseWindow();

    return 0;
}
