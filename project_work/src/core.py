"""Motore di esecuzione: baseline sequenziale + backend paralleli.

Contiene:
  * lo stato globale del worker (ereditato dai processi figli tramite fork);
  * la funzione di lavoro applicata a un chunk di indici;
  * i runner: sequenziale, ProcessPoolExecutor/Pool, ThreadPool;
  * le strategie di scheduling: static (p blocchi contigui) e dynamic (molti
    chunk piccoli assegnati on demand);
  * la misura di wall-clock time, CPU time del master e CPU time dei figli.

Scelte di progetto rilevanti per il benchmark
--------------------------------------------
1. *Seed per immagine*: prima di ogni immagine la pipeline viene reinizializzata
   con seed = base_seed + indice. L'output dipende quindi solo dall'indice
   dell'immagine e non da quale worker la elabora, ne' dall'ordine, ne' dalla
   dimensione dei chunk. Sequenziale e parallelo producono percio' output
   *bit-identici* (requisito 5), pur restando l'augmentation randomica.
2. *Trasferimento dei risultati*: per default i worker restituiscono una
   riduzione scalare per immagine (somma dei pixel) invece dell'immagine
   augmentata. Cosi' il benchmark misura il costo di calcolo e non il costo di
   serializzazione IPC. La modalita' "array" e' disponibile per quantificare
   esattamente quell'overhead (requisito 17).
3. *Dataset condiviso*: con start method `fork` le immagini gia' in RAM nel
   processo padre sono visibili ai figli in copy-on-write, senza pickling.
"""
from __future__ import annotations

import hashlib
import multiprocessing as mp
import os
import resource
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import cv2
import numpy as np

from . import pipelines

cv2.setNumThreads(0)

# ---------------------------------------------------------------------------
# stato globale del worker
# ---------------------------------------------------------------------------

_STATE: dict[str, Any] = {
    "images": None,      # list[np.ndarray] | None  (dataset in RAM)
    "paths": None,       # list[str] | None         (dataset su disco, end-to-end)
    "out_dir": None,
    "level": "medium",
    "base_seed": 1234,
    "return_mode": "reduce",   # reduce | digest | array
    "resize_last": False,      # pipeline a risoluzione nativa (load balancing)
}

_local = threading.local()


def set_state(**kwargs) -> None:
    """Configura lo stato del processo padre prima di creare il pool."""
    _STATE.update(kwargs)
    _local.__dict__.pop("pipeline", None)
    _local.__dict__.pop("pipeline_key", None)


#: chiavi dello stato che contengono i DATI (potenzialmente gigabyte). Con `fork`
#: i figli le ereditano gratis in copy-on-write; con `spawn`/`forkserver` invece
#: verrebbero serializzate e spedite a OGNI worker, quindi non vanno mai messe
#: negli initargs del pool.
_BULK_KEYS = ("images", "paths")


def light_state() -> dict[str, Any]:
    """Stato senza i dati: sicuro da inviare a un worker via pickle."""
    return {k: v for k, v in _STATE.items() if k not in _BULK_KEYS}


def _init_worker(state: dict[str, Any]) -> None:
    """Initializer usato dai start method che non ereditano la memoria (spawn)."""
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    cv2.setNumThreads(0)
    _STATE.update(state)


def _pipeline() -> Any:
    """Pipeline thread-local: Compose ha stato interno (RNG) e non e' condivisibile."""
    key = (_STATE["level"], _STATE["resize_last"])
    if getattr(_local, "pipeline", None) is None or _local.pipeline_key != key:
        _local.pipeline = pipelines.build(key[0], resize_last=key[1])
        _local.pipeline_key = key
    return _local.pipeline


# ---------------------------------------------------------------------------
# unita' di lavoro
# ---------------------------------------------------------------------------


@dataclass
class TaskResult:
    """Esito di un chunk: payload + contabilita' per l'analisi del bilanciamento."""

    indices: list[int]
    payload: list
    pid: int
    t_start: float
    t_end: float

    @property
    def duration(self) -> float:
        return self.t_end - self.t_start


def _finish(image: np.ndarray, mode: str) -> Any:
    if mode == "reduce":
        # riduzione scalare: costa ~20 us su 256x256x3, evita il costo IPC
        return int(image.sum(dtype=np.int64))
    if mode == "digest":
        return hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()
    if mode == "array":
        return image
    raise ValueError(f"return_mode sconosciuto: {mode}")


def augment_chunk(indices: Sequence[int]) -> TaskResult:
    """Applica la pipeline alle immagini in RAM indicate da `indices`."""
    t0 = time.perf_counter()
    images = _STATE["images"]
    pipe = _pipeline()
    base_seed = _STATE["base_seed"]
    mode = _STATE["return_mode"]
    out = []
    for idx in indices:
        pipe.set_random_seed(base_seed + idx)
        res = pipe(image=images[idx])
        out.append(_finish(res["image"], mode))
    return TaskResult(list(indices), out, os.getpid(), t0, time.perf_counter())


def augment_chunk_e2e(indices: Sequence[int]) -> TaskResult:
    """Variante end-to-end: legge da disco, augmenta e riscrive su disco."""
    t0 = time.perf_counter()
    paths = _STATE["paths"]
    out_dir = _STATE["out_dir"]
    pipe = _pipeline()
    base_seed = _STATE["base_seed"]
    written = []
    for idx in indices:
        bgr = cv2.imread(paths[idx], cv2.IMREAD_COLOR)
        image = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pipe.set_random_seed(base_seed + idx)
        aug = pipe(image=image)["image"]
        dst = os.path.join(out_dir, f"aug_{idx:06d}.jpg")
        cv2.imwrite(dst, cv2.cvtColor(aug, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        written.append(dst)
    return TaskResult(list(indices), written, os.getpid(), t0, time.perf_counter())


# ---------------------------------------------------------------------------
# costruzione dei task
# ---------------------------------------------------------------------------


def split_static(indices: Sequence[int], workers: int) -> list[list[int]]:
    """Assegnamento statico: esattamente `workers` blocchi contigui."""
    n = len(indices)
    base, extra = divmod(n, workers)
    chunks, start = [], 0
    for w in range(workers):
        size = base + (1 if w < extra else 0)
        if size:
            chunks.append(list(indices[start:start + size]))
        start += size
    return chunks


def split_chunks(indices: Sequence[int], chunksize: int) -> list[list[int]]:
    """Assegnamento dinamico: tanti chunk di dimensione fissa, dispatch on demand."""
    chunksize = max(1, int(chunksize))
    return [list(indices[i:i + chunksize]) for i in range(0, len(indices), chunksize)]


def build_tasks(indices: Sequence[int], workers: int, scheduling: str, chunksize: int | None) -> list[list[int]]:
    if scheduling == "static":
        return split_static(indices, workers)
    if scheduling == "dynamic":
        if chunksize is None:
            raise ValueError("scheduling dinamico richiede chunksize")
        return split_chunks(indices, chunksize)
    raise ValueError(f"scheduling sconosciuto: {scheduling}")


# ---------------------------------------------------------------------------
# misura del tempo
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Tutte le metriche grezze di una singola esecuzione."""

    n_images: int
    workers: int
    mode: str
    wall_total: float          # metrica principale: pool + calcolo + shutdown
    wall_compute: float        # solo la fase di map (senza creazione pool)
    pool_setup: float          # creazione/distruzione dei processi
    cpu_main: float            # CPU time del processo master (user+sys)
    cpu_children: float        # CPU time cumulativo dei figli (user+sys)
    tasks: int
    payload: list = field(default_factory=list, repr=False)
    worker_busy: dict[int, float] = field(default_factory=dict)
    task_durations: list[float] = field(default_factory=list, repr=False)

    @property
    def cpu_total(self) -> float:
        return self.cpu_main + self.cpu_children

    @property
    def throughput(self) -> float:
        return self.n_images / self.wall_total if self.wall_total else float("nan")

    @property
    def imbalance(self) -> float:
        """max/mean del tempo occupato per worker: 1.0 = bilanciamento perfetto."""
        if not self.worker_busy:
            return float("nan")
        vals = list(self.worker_busy.values())
        mean = sum(vals) / len(vals)
        return max(vals) / mean if mean else float("nan")


def _children_cpu() -> float:
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    return ru.ru_utime + ru.ru_stime


def _self_cpu() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return ru.ru_utime + ru.ru_stime


def _collect(results: Iterable[TaskResult], keep_payload: bool) -> tuple[list, dict[int, float], list[float]]:
    payload, busy, durs = [], {}, []
    for r in results:
        if keep_payload:
            payload.extend(zip(r.indices, r.payload))
        busy[r.pid] = busy.get(r.pid, 0.0) + r.duration
        durs.append(r.duration)
    return payload, busy, durs


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


def run_sequential(indices: Sequence[int], *, work: Callable = augment_chunk,
                   keep_payload: bool = False, chunksize: int | None = None) -> RunResult:
    """Baseline T_1: un solo processo, un solo thread, nessun overhead parallelo."""
    tasks = split_chunks(indices, chunksize) if chunksize else [list(indices)]
    cpu0, wall0 = _self_cpu(), time.perf_counter()
    results = [work(t) for t in tasks]
    wall = time.perf_counter() - wall0
    cpu = _self_cpu() - cpu0
    payload, busy, durs = _collect(results, keep_payload)
    return RunResult(len(indices), 1, "sequential", wall, wall, 0.0, cpu, 0.0,
                     len(tasks), payload, busy, durs)


def run_process_pool(indices: Sequence[int], workers: int, *, scheduling: str = "dynamic",
                     chunksize: int | None = 16, work: Callable = augment_chunk,
                     keep_payload: bool = False, start_method: str = "fork",
                     maxtasksperchild: int | None = None) -> RunResult:
    """Esecuzione parallela con multiprocessing.Pool.

    I task sono liste di indici; `pool.map(..., chunksize=1)` fa si' che ogni
    task sia dispatchato individualmente, quindi la granularita' e' decisa
    unicamente da come costruiamo i chunk (static vs dynamic).
    """
    tasks = build_tasks(indices, workers, scheduling, chunksize)
    if start_method != "fork" and any(_STATE.get(k) is not None for k in _BULK_KEYS):
        raise ValueError(
            f"start_method={start_method!r} non e' supportato con un dataset in memoria: "
            "senza fork i dati non sono ereditati in copy-on-write e verrebbero "
            "serializzati e copiati in ogni worker (per il dataset principale sono "
            "~2.2 GB a worker, cioe' esaurimento della RAM). Usare start_method='fork', "
            "oppure far ricaricare il dataset a ogni worker dentro l'initializer."
        )
    ctx = mp.get_context(start_method)
    init_args = (light_state(),) if start_method != "fork" else None

    cpu_child0, cpu_main0 = _children_cpu(), _self_cpu()
    wall0 = time.perf_counter()
    pool = ctx.Pool(processes=workers,
                    initializer=_init_worker if init_args else None,
                    initargs=init_args or (),
                    maxtasksperchild=maxtasksperchild)
    setup = time.perf_counter() - wall0
    try:
        map0 = time.perf_counter()
        results = pool.map(work, tasks, chunksize=1)
        compute = time.perf_counter() - map0
    finally:
        pool.close()
        pool.join()
    wall_total = time.perf_counter() - wall0
    cpu_children = _children_cpu() - cpu_child0
    cpu_main = _self_cpu() - cpu_main0

    payload, busy, durs = _collect(results, keep_payload)
    return RunResult(len(indices), workers, f"process/{scheduling}", wall_total, compute,
                     setup + (wall_total - setup - compute), cpu_main, cpu_children,
                     len(tasks), payload, busy, durs)


def run_thread_pool(indices: Sequence[int], workers: int, *, scheduling: str = "dynamic",
                    chunksize: int | None = 16, work: Callable = augment_chunk,
                    keep_payload: bool = False) -> RunResult:
    """Versione a thread: mostra quanto GIL/OpenCV limitano il parallelismo interno."""
    tasks = build_tasks(indices, workers, scheduling, chunksize)
    cpu0 = time.process_time()
    wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        setup = time.perf_counter() - wall0
        map0 = time.perf_counter()
        results = list(ex.map(work, tasks))
        compute = time.perf_counter() - map0
    wall_total = time.perf_counter() - wall0
    cpu_main = time.process_time() - cpu0
    payload, busy, durs = _collect(results, keep_payload)
    # con i thread il pid e' unico: il bilanciamento si misura sui task
    return RunResult(len(indices), workers, f"thread/{scheduling}", wall_total, compute,
                     setup, cpu_main, 0.0, len(tasks), payload, {}, durs)


BACKENDS = {"process": run_process_pool, "thread": run_thread_pool}


def run_parallel(indices: Sequence[int], workers: int, *, backend: str = "process", **kw) -> RunResult:
    if backend not in BACKENDS:
        raise ValueError(f"backend sconosciuto: {backend}")
    return BACKENDS[backend](indices, workers, **kw)


def run_with_pool(pool, indices: Sequence[int], workers: int, *, scheduling: str = "dynamic",
                  chunksize: int | None = 16, work: Callable = augment_chunk,
                  keep_payload: bool = False) -> RunResult:
    """Esegue un batch su un pool GIA' esistente (creazione dei processi ammortizzata).

    E' il modo in cui lavora una pipeline reale di training: il pool viene creato
    una volta sola e riutilizzato per tutte le epoche. Qui `pool_setup` e'
    azzerato e `cpu_children` non e' misurabile (i figli non vengono raccolti),
    quindi vale 0.
    """
    tasks = build_tasks(indices, workers, scheduling, chunksize)
    cpu_main0 = _self_cpu()
    wall0 = time.perf_counter()
    results = pool.map(work, tasks, chunksize=1)
    wall = time.perf_counter() - wall0
    payload, busy, durs = _collect(results, keep_payload)
    return RunResult(len(indices), workers, f"process-persistent/{scheduling}", wall, wall,
                     0.0, _self_cpu() - cpu_main0, 0.0, len(tasks), payload, busy, durs)


def time_pool_creation(workers: int, start_method: str = "fork") -> tuple[float, float]:
    """Ritorna (tempo di creazione, tempo di distruzione) di un pool vuoto.

    Ai worker viene passato solo lo stato leggero (`light_state`): la misura
    riguarda il costo di *creazione dei processi*, non il costo di spedire loro
    il dataset. Includere le immagini negli initargs, con `spawn`, significa
    serializzare l'intero dataset una volta per worker.
    """
    ctx = mp.get_context(start_method)
    init_args = (light_state(),) if start_method != "fork" else ()
    t0 = time.perf_counter()
    pool = ctx.Pool(processes=workers,
                    initializer=_init_worker if init_args else None,
                    initargs=init_args)
    pool.map(int, [0] * workers, chunksize=1)  # forza l'avvio effettivo dei processi
    t1 = time.perf_counter()
    pool.close()
    pool.join()
    return t1 - t0, time.perf_counter() - t1
