# Progetto di parallel computing

Questa repository contiene due progetti sviluppati per l'esame di parallel computing. 

La repository è divisa in due moduli principali:
1. **Boids**: Una simulazione di stormi in C.
2. **Password decryption**: Un tool di decrittazione parallela di hash DES in Python.

---
## Progetto 1: Boids
Una simulazione visiva del comportamento degli stormi (Boids), scritta in **C** e parallelizzata con **OpenMP**. L'applicazione utilizza **Raylib** per il rendering grafico 

### Requisiti
Per compilare il progetto sono necessari:
- GCC
- Supporto a OpenMP (`libgomp`)
- Raylib (`libraylib`)
- OpenGL (`libGL`), X11 (`libX11`), Math (`libm`), Pthreads (`lpthread`)

### Compilazione
Il progetto include un `Makefile` completo per la gestione delle build. Tutti gli eseguibili verranno generati nella cartella `bin/`.

```bash
# Compila tutti gli eseguibili (Release ottimizzata)
make all

# Compila in modalità Debug (con flag -g)
make debug

# Pulisce i file oggetto e gli eseguibili
make clean

# Esempio di esecuzione
./bin/boids --grid 5000 --seed 42 
```
---
## Progetto 2: Passwords decryption
Questo progetto implementa un sistema per la decifratura di password (brute force) basate su date temporali, utilizzando l'algoritmo DES.

### Architettura del Sistema
Il progetto mette a confronto due approcci architetturali:
Shared-Nothing: Ogni worker è isolato. La comunicazione avviene solo tramite messaggi IPC all'inizio e alla fine del task. Nessuna memoria condivisa.
Global Early Exit: Utilizza una struttura dati condivisa per segnalare il ritrovamento della password.

### Requisiti
```bash
# Librerie necessarie
pip install passlib matplotlib pandas
