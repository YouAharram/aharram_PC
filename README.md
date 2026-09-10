# Progetto di parallel computing

Questa repository contiene i progetti sviluppati per l'esame di parallel computing. 

La repository è divisa in tre moduli principali:
1. **Boids**: Una simulazione di stormi in C.
2. **Password decryption**: Un tool di decrittazione parallela di hash DES in Python.
3. **Project work**: Uno studio sperimentale sulla parallelizzazione della data augmentation di immagini in Python.

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
```

---
## Progetto 3: Project work — Data augmentation parallela
Uno studio sperimentale sulla parallelizzazione di una pipeline di **data augmentation** di immagini in **Python**, tipica del pre-processing per l'addestramento di reti neurali. L'obiettivo non è solo velocizzare il calcolo, ma **misurare e spiegare** il comportamento del parallelismo su CPU multicore: speedup, efficienza, overhead, bilanciamento del carico e limiti fisici della macchina.

La pipeline di augmentation è costruita con **Albumentations** e **OpenCV**, e viene parallelizzata con `multiprocessing.Pool` (backend a processi) e `ThreadPoolExecutor` (backend a thread), confrontando le due strategie contro una baseline sequenziale.

### Scelte di progetto principali
- **Shared-Nothing con `fork`**: il dataset viene generato in RAM nel processo padre e condiviso ai worker in *copy-on-write* grazie allo start method `fork`, evitando la serializzazione (pickling) del dataset a ogni worker.
- **Output bit-identici**: ogni immagine usa un seed derivato dal proprio indice (`base_seed + indice`), quindi il risultato è indipendente dall'ordine, dal worker e dalla dimensione dei chunk. Sequenziale e parallelo producono lo stesso output.
- **Tre livelli di workload**: pipeline `light` / `medium` / `heavy` a costo computazionale crescente, per studiare come la convenienza del parallelismo dipenda dalla granularità del lavoro per immagine.
- **Scheduling statico e dinamico**: blocchi contigui (`static`) contro molti chunk piccoli assegnati on-demand (`dynamic`), per analizzare granularità e bilanciamento del carico.

### Struttura
```
project_work/
├── src/            # motore: dataset, pipeline, runner paralleli, benchmark, plotting
├── experiments/    # gli esperimenti eseguibili (01..09)
├── results/        # output grezzi (CSV / JSON / log)
├── figures/        # figure generate per la relazione
├── data/           # dataset in cache e immagini per l'end-to-end
└── Relazione.pdf   # relazione completa con analisi dei risultati
```

### Esperimenti
| # | Esperimento | Cosa misura |
|---|-------------|-------------|
| 01 | Correttezza | Output sequenziale = parallelo (immagini e annotazioni) |
| 02 | Strong scaling | Speedup ed efficienza a problema fisso, sui tre workload |
| 03 | Weak scaling | Carico costante per worker al crescere dei worker |
| 04 | Chunk size | Effetto della granularità dei chunk |
| 05 | Load balancing | Statico vs dinamico su task a costo eterogeneo |
| 06 | End-to-end | Pipeline realistica: lettura, augmentation e scrittura su disco |
| 07 | Overhead | Costo di creazione del pool e di comunicazione IPC |

### Requisiti
```bash
# Librerie necessarie
pip install albumentations opencv-python numpy pandas matplotlib psutil
```

### Esecuzione
Ogni esperimento è uno script indipendente che genera i risultati in `results/`; le figure vengono poi prodotte da `src/plots.py`.

```bash
cd project_work

# Esegue un esperimento (es. strong scaling)
python experiments/02_strong_scaling.py

# Genera tutte le figure a partire dai risultati
python src/plots.py
```
