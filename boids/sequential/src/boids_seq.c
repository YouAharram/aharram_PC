#include "../include/boids.h"
#include <math.h>

void update_boids_sequential(Boid* in, Boid* out, int n) {
    for (int i = 0; i < n; i++) {
        float xpos_avg = 0, ypos_avg = 0;
        float xvel_avg = 0, yvel_avg = 0;
        int neighboring_boids = 0;
        float close_dx = 0, close_dy = 0;

        float boid_x = in[i].x;
        float boid_y = in[i].y;
        float boid_vx = in[i].vx;
        float boid_vy = in[i].vy;

        for (int j = 0; j < n; j++) {
            if (i == j) continue; 

            float dx = boid_x - in[j].x;
            float dy = boid_y - in[j].y;

            if (fabsf(dx) < VISUAL_RANGE && fabsf(dy) < VISUAL_RANGE) {
                float squared_distance = dx*dx + dy*dy;

                if (squared_distance < PROTECTED_RANGE_SQ) {
                    close_dx += boid_x - in[j].x;
                    close_dy += boid_y - in[j].y;
                }
                else if (squared_distance < VISUAL_RANGE_SQ) {
                    xpos_avg += in[j].x;
                    ypos_avg += in[j].y;
                    xvel_avg += in[j].vx;
                    yvel_avg += in[j].vy;
                    neighboring_boids++;
                }
            }
        }

        float next_vx = boid_vx;
        float next_vy = boid_vy;

        if (neighboring_boids > 0) {
            xpos_avg /= neighboring_boids;
            ypos_avg /= neighboring_boids;
            xvel_avg /= neighboring_boids;
            yvel_avg /= neighboring_boids;

            next_vx += (xpos_avg - boid_x) * CENTERING_FACTOR + 
                       (xvel_avg - boid_vx) * MATCHING_FACTOR;
            next_vy += (ypos_avg - boid_y) * CENTERING_FACTOR + 
                       (yvel_avg - boid_vy) * MATCHING_FACTOR;
        }

        next_vx += (close_dx * AVOID_FACTOR);
        next_vy += (close_dy * AVOID_FACTOR);

        if (boid_y < 50)  next_vy += TURN_FACTOR;
        if (boid_y > SCREEN_HEIGHT - 50) next_vy -= TURN_FACTOR;
        if (boid_x < 50)  next_vx += TURN_FACTOR;
        if (boid_x > SCREEN_WIDTH - 50)  next_vx -= TURN_FACTOR;

        float speed = sqrtf(next_vx * next_vx + next_vy * next_vy);
        if (speed > 0) { 
            if (speed < BOID_MIN_SPEED) {
                next_vx = (next_vx / speed) * BOID_MIN_SPEED;
                next_vy = (next_vy / speed) * BOID_MIN_SPEED;
            }
            if (speed > BOID_MAX_SPEED) {
                next_vx = (next_vx / speed) * BOID_MAX_SPEED;
                next_vy = (next_vy / speed) * BOID_MAX_SPEED;
            }
        }

        out[i].vx = next_vx;
        out[i].vy = next_vy;
        out[i].x = boid_x + next_vx;
        out[i].y = boid_y + next_vy;
    }
}

void build_grid(Boid* flock, int n, Cell (*grid)[GRID_COLS]) {
    for (int r = 0; r < GRID_ROWS; r++) {
        for (int c = 0; c < GRID_COLS; c++) {
            grid[r][c].count = 0;
        }
    }

    for (int i = 0; i < n; i++) {
        int col = (int)(flock[i].x / CELL_SIZE);
        int row = (int)(flock[i].y / CELL_SIZE);

        if (col >= 0 && col < GRID_COLS && row >= 0 && row < GRID_ROWS) {
            int current_count = grid[row][col].count;
            if (current_count < MAX_BOIDS_PER_CELL) {
                grid[row][col].boid_indices[current_count] = i;
                grid[row][col].count++;
            }
        }
    }
}

void update_boids_grid_sequential(Boid* in, Boid* out, int n, Cell (*grid)[GRID_COLS]) {
    for (int i = 0; i < n; i++) {
        float xpos_avg = 0, ypos_avg = 0;
        float xvel_avg = 0, yvel_avg = 0;
        int neighboring_boids = 0;
        float close_dx = 0, close_dy = 0;

        float boid_x = in[i].x;
        float boid_y = in[i].y;
        float boid_vx = in[i].vx;
        float boid_vy = in[i].vy;

        int boid_col = (int)(boid_x / CELL_SIZE);
        int boid_row = (int)(boid_y / CELL_SIZE);

        for (int dr = -1; dr <= 1; dr++) {
            for (int dc = -1; dc <= 1; dc++) {
                int r = boid_row + dr;
                int c = boid_col + dc;

                if (r >= 0 && r < GRID_ROWS && c >= 0 && c < GRID_COLS) {
                    Cell* cell = &grid[r][c];
                    
                    for (int k = 0; k < cell->count; k++) {
                        int j = cell->boid_indices[k];
                        if (i == j) continue;

                        float dx = boid_x - in[j].x;
                        float dy = boid_y - in[j].y;

                        if (fabsf(dx) < VISUAL_RANGE && fabsf(dy) < VISUAL_RANGE) {
                            float squared_distance = dx*dx + dy*dy;

                            if (squared_distance < PROTECTED_RANGE_SQ) {
                                close_dx += boid_x - in[j].x;
                                close_dy += boid_y - in[j].y;
                            }
                            else if (squared_distance < VISUAL_RANGE_SQ) {
                                xpos_avg += in[j].x;
                                ypos_avg += in[j].y;
                                xvel_avg += in[j].vx;
                                yvel_avg += in[j].vy;
                                neighboring_boids++;
                            }
                        }
                    }
                }
            }
        }

        float next_vx = boid_vx;
        float next_vy = boid_vy;

        if (neighboring_boids > 0) {
            xpos_avg /= neighboring_boids;
            ypos_avg /= neighboring_boids;
            xvel_avg /= neighboring_boids;
            yvel_avg /= neighboring_boids;

            next_vx += (xpos_avg - boid_x) * CENTERING_FACTOR + (xvel_avg - boid_vx) * MATCHING_FACTOR;
            next_vy += (ypos_avg - boid_y) * CENTERING_FACTOR + (yvel_avg - boid_vy) * MATCHING_FACTOR;
        }

        next_vx += (close_dx * AVOID_FACTOR);
        next_vy += (close_dy * AVOID_FACTOR);

        if (boid_y < 50) next_vy += TURN_FACTOR;
        if (boid_y > SCREEN_HEIGHT - 50) next_vy -= TURN_FACTOR;
        if (boid_x < 50) next_vx += TURN_FACTOR;
        if (boid_x > SCREEN_WIDTH - 50) next_vx -= TURN_FACTOR;

        float speed = sqrtf(next_vx * next_vx + next_vy * next_vy);
        if (speed > 0) {
            if (speed < BOID_MIN_SPEED) {
                next_vx = (next_vx / speed) * BOID_MIN_SPEED;
                next_vy = (next_vy / speed) * BOID_MIN_SPEED;
            }
            if (speed > BOID_MAX_SPEED) {
                next_vx = (next_vx / speed) * BOID_MAX_SPEED;
                next_vy = (next_vy / speed) * BOID_MAX_SPEED;
            }
        }

        out[i].vx = next_vx;
        out[i].vy = next_vy;
        out[i].x = boid_x + next_vx;
        out[i].y = boid_y + next_vy;
    }
}
