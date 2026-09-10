"""Parametri centrali di tutti gli esperimenti.

Dimensionati sulla macchina di test (i7-1280P, 14 core fisici / 20 logici,
15 GB di RAM) in modo che:
  * il tempo sequenziale sia abbastanza lungo da rendere trascurabile il rumore
    di misura (>= ~1 s, e ~15 s per il workload pesante);
  * il dataset in RAM resti sotto ~2.5 GB (condiviso in copy-on-write tra i
    worker grazie allo start method `fork`).
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Le directory di output sono sovrascrivibili da variabili d'ambiente: comodo per
# provare la catena figure/relazione su dati di prova senza toccare i risultati veri.
RESULTS = Path(os.environ.get("PW_RESULTS", ROOT / "results"))
FIGURES = Path(os.environ.get("PW_FIGURES", ROOT / "figures"))
DATA = Path(os.environ.get("PW_DATA", ROOT / "data"))
CACHE = DATA / "cache"

# --- dataset -----------------------------------------------------------------
IMAGE_SIZE = 512          # lato delle immagini sorgente (l'output e' 256x256)
N_IMAGES = 3000           # dataset principale (~2.36 GB in RAM)
BASE_SEED = 1234          # seed dell'augmentation (seed per immagine = BASE_SEED + indice)
DATASET_SEED = 20250908   # seed di generazione del dataset

# --- sweep del numero di worker ----------------------------------------------
LOGICAL_CORES = os.cpu_count() or 8
PHYSICAL_CORES = 14
# include punti oltre il numero di core logici per mostrare l'oversubscription
WORKERS = [1, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 32, 40]
WORKERS_SHORT = [1, 2, 4, 8, 14, 20, 32]

# --- ripetizioni --------------------------------------------------------------
# Sovrascrivibili da ambiente (PW_REPS / PW_WARMUPS): la modalita' rapida di
# run_quick.sh le abbassa per validare la catena in pochi minuti.
REPS = int(os.environ.get("PW_REPS", 7))
WARMUPS = int(os.environ.get("PW_WARMUPS", 2))

# --- granularita' di default --------------------------------------------------
CHUNKSIZE = 16            # chunk usato negli esperimenti che non lo variano
CHUNK_SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1500, 3000]

# --- weak scaling -------------------------------------------------------------
WEAK_PER_WORKER = 500     # immagini per worker (il carico per worker resta costante)
WEAK_WORKERS = [1, 2, 4, 8, 14, 20]

# --- load balancing -----------------------------------------------------------
HETERO_N = 1500
HETERO_SIZES = (192, 320, 512, 832)
HETERO_WEIGHTS = (0.55, 0.25, 0.15, 0.05)
HETERO_WORKERS = [4, 8, 14]

# --- end-to-end ---------------------------------------------------------------
E2E_N = 1500
E2E_IN = DATA / "e2e_in"
E2E_OUT = DATA / "e2e_out"
E2E_WORKERS = [1, 2, 4, 8, 14, 20]
E2E_REPS = 5

for _d in (RESULTS, FIGURES, CACHE):
    _d.mkdir(parents=True, exist_ok=True)
