# Progetto di parallel computing

Questa repository contiene due progetti sviluppati per l'esame di parallel computing. 

La repository è divisa in due moduli principali:
1. **Boids**: Una simulazione di stormi in C.
2. **Password decryption**: Un tool di decrittazione parallela di hash DES in Python.

---
## Progetto 1: Boids
Una simulazione visiva del comportamento degli stormi (Boids), scritta in **C** e parallelizzata con **OpenMP**. L'applicazione utilizza **Raylib** per il rendering grafico 

### 🛠️ Caratteristiche Tecniche e Ottimizzazioni
- **OpenMP Multi-threading:** Il calcolo delle forze (separazione, allineamento, coesione) è parallelizzato per sfruttare tutti i core disponibili della CPU.
- **Data-Oriented Design (SOA):** Utilizzo della *Structure of Arrays* (SOA) per massimizzare la cache hit-rate rispetto alla classica *Array of Structures* (AOS).
- **SIMD / Vettorizzazione:** Compilazione con `-O3`, `-march=native` e `-ffast-math` per favorire l'auto-vettorizzazione da parte del compilatore.
- **Benchmarking Integrato:** Suite di eseguibili dedicati all'analisi delle performance (Strong Scaling, Weak Scaling, Chunk Scaling).

### ⚙️ Requisiti
Per compilare il progetto sono necessari:
- GCC
- Supporto a OpenMP (`libgomp`)
- Raylib (`libraylib`)
- OpenGL (`libGL`), X11 (`libX11`), Math (`libm`), Pthreads (`lpthread`)

### 🏗️ Compilazione
Il progetto include un `Makefile` completo per la gestione delle build. Tutti gli eseguibili verranno generati nella cartella `bin/`.

```bash
# Compila tutti gli eseguibili (Release ottimizzata)
make all

# Compila in modalità Debug (con flag -g)
make debug

# Pulisce i file oggetto e gli eseguibili
make clean
