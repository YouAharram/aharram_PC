#!/usr/bin/env python
"""Esperimento 7 - Anatomia dell'overhead di parallelizzazione (requisiti 15 e 17).

Non basta dire che lo speedup non e' lineare: qui ogni singola sorgente di
overhead viene isolata e misurata.

  A. costo di creazione dei processi, in funzione del numero di worker, dello
     start method (fork/spawn/forkserver) e dell'impronta di memoria del padre;
  B. costo di comunicazione: risultati come riduzione scalare vs immagine
     completa restituita al master (196 KB per immagine da serializzare);
  C. pool persistente vs pool ricreato a ogni batch (ammortizzazione del setup);
  D. thread vs processi: quanto il GIL limita, e quanto OpenCV lo rilascia;
  E. parallelismo *intra*-immagine (thread interni di OpenCV) confrontato con il
     parallelismo *inter*-immagine adottato nel progetto;
  F. CPU time totale vs wall-clock: quanto lavoro in piu' costa il parallelismo.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2        # noqa: E402
import psutil     # noqa: E402

from src import bench, core, dataset, sysinfo   # noqa: E402
from src import config as C                     # noqa: E402


def rss_gb() -> float:
    return psutil.Process().memory_info().rss / 1024**3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=C.N_IMAGES)
    ap.add_argument("--reps", type=int, default=5)
    args = ap.parse_args()

    rec = bench.Recorder("07_overhead", C.RESULTS)
    rec.meta.update(system=sysinfo.collect(), n_images=args.n, reps=args.reps)
    workers_sweep = [1, 2, 4, 8, 14, 20, 32]

    # ------------------------------------------------------------------ A (piccolo)
    print("=== [A] costo di creazione del pool ===")
    print("  padre 'leggero' (100 immagini, ~78 MB):")
    small = dataset.make_memory_dataset(100, C.IMAGE_SIZE, base_seed=C.DATASET_SEED)
    core.set_state(images=small, level="light", base_seed=C.BASE_SEED, return_mode="reduce")
    small_rss = rss_gb()
    for method in ("fork", "spawn", "forkserver"):
        for p in workers_sweep:
            ts = [core.time_pool_creation(p, method) for _ in range(3)]
            create, destroy = st.median(t[0] for t in ts), st.median(t[1] for t in ts)
            rec.add({"section": "A_pool_creation", "start_method": method, "workers": p,
                     "parent_rss_gb": round(small_rss, 3), "parent_dataset": "small_100",
                     "create_s": create, "destroy_s": destroy, "total_s": create + destroy,
                     "per_worker_ms": (create + destroy) / p * 1000})
            print(f"    {method:<11s} p={p:<3d} create={create * 1000:7.1f}ms "
                  f"destroy={destroy * 1000:6.1f}ms  ({(create + destroy) / p * 1000:5.2f} ms/worker)")
    del small

    print(f"\n  padre 'pesante' (dataset completo, {args.n} immagini):")
    images = dataset.load_or_make(args.n, C.IMAGE_SIZE, cache_dir=C.CACHE, base_seed=C.DATASET_SEED)
    core.set_state(images=images, level="light", base_seed=C.BASE_SEED, return_mode="reduce")
    big_rss = rss_gb()
    print(f"  RSS del processo padre: {big_rss:.2f} GB")
    for method in ("fork", "spawn"):
        for p in workers_sweep:
            ts = [core.time_pool_creation(p, method) for _ in range(3)]
            create, destroy = st.median(t[0] for t in ts), st.median(t[1] for t in ts)
            rec.add({"section": "A_pool_creation", "start_method": method, "workers": p,
                     "parent_rss_gb": round(big_rss, 3), "parent_dataset": f"full_{args.n}",
                     "create_s": create, "destroy_s": destroy, "total_s": create + destroy,
                     "per_worker_ms": (create + destroy) / p * 1000})
            print(f"    {method:<11s} p={p:<3d} create={create * 1000:7.1f}ms "
                  f"destroy={destroy * 1000:6.1f}ms  ({(create + destroy) / p * 1000:5.2f} ms/worker)")

    # ------------------------------------------------------------------ B
    print("\n=== [B] costo di comunicazione dei risultati (IPC) ===")
    n_ipc = min(1500, args.n)
    idx_ipc = list(range(n_ipc))
    for level in ("light", "heavy"):
        for mode in ("reduce", "array"):
            core.set_state(images=images, level=level, base_seed=C.BASE_SEED, return_mode=mode)
            seq = bench.repeat(lambda: core.run_sequential(idx_ipc), args.reps, 1, label="seq")
            t1 = bench.summarize(seq)["time_median"]
            rec.add(bench.summarize(seq, baseline_median=t1) |
                    {"section": "B_ipc", "level": level, "return_mode": mode, "backend": "sequential"})
            for p in (2, 4, 8, 14, 20):
                runs = bench.repeat(lambda p=p: core.run_process_pool(idx_ipc, p, chunksize=C.CHUNKSIZE),
                                    args.reps, 1, label=f"p={p}")
                r = bench.summarize(runs, baseline_median=t1)
                r.update(section="B_ipc", level=level, return_mode=mode, backend="process")
                rec.add(r)
                print(f"  {level:<6s} {mode:<7s} p={p:<3d} T={r['time_median']:7.3f}s "
                      f"S={r['speedup']:5.2f}x  ({n_ipc} img)")
    core.set_state(return_mode="reduce")

    # ------------------------------------------------------------------ C
    print("\n=== [C] pool persistente vs pool ricreato a ogni batch ===")
    for level in ("light", "medium", "heavy"):
        core.set_state(images=images, level=level, base_seed=C.BASE_SEED, return_mode="reduce")
        idx = list(range(args.n))
        seq = bench.repeat(lambda: core.run_sequential(idx), args.reps, C.WARMUPS, label="seq")
        t1 = bench.summarize(seq)["time_median"]
        rec.add(bench.summarize(seq, baseline_median=t1) |
                {"section": "C_persistent", "level": level, "pool": "sequential"})
        for p in (8, 14, 20):
            runs = bench.repeat(lambda p=p: core.run_process_pool(idx, p, chunksize=C.CHUNKSIZE),
                                args.reps, C.WARMUPS, label=f"fresh p={p}")
            fresh = bench.summarize(runs, baseline_median=t1)
            fresh.update(section="C_persistent", level=level, pool="fresh")
            rec.add(fresh)

            ctx = mp.get_context("fork")
            pool = ctx.Pool(processes=p)
            try:
                runs = bench.repeat(
                    lambda p=p: core.run_with_pool(pool, idx, p, chunksize=C.CHUNKSIZE),
                    args.reps, C.WARMUPS, label=f"persist p={p}")
            finally:
                pool.close()
                pool.join()
            pers = bench.summarize(runs, baseline_median=t1)
            pers.update(section="C_persistent", level=level, pool="persistent")
            rec.add(pers)
            print(f"  {level:<6s} p={p:<3d} fresh S={fresh['speedup']:5.2f}x -> "
                  f"persistente S={pers['speedup']:5.2f}x  "
                  f"(setup evitato: {fresh['pool_setup_median'] * 1000:.0f} ms)")

    # ------------------------------------------------------------------ D
    print("\n=== [D] thread vs processi ===")
    n_td = min(1500, args.n)
    idx_td = list(range(n_td))
    for level in ("light", "medium", "heavy"):
        core.set_state(images=images, level=level, base_seed=C.BASE_SEED, return_mode="reduce")
        seq = bench.repeat(lambda: core.run_sequential(idx_td), args.reps, C.WARMUPS, label="seq")
        t1 = bench.summarize(seq)["time_median"]
        rec.add(bench.summarize(seq, baseline_median=t1) |
                {"section": "D_backend", "level": level, "backend": "sequential"})
        for backend in ("thread", "process"):
            for p in (2, 4, 8, 14, 20):
                runs = bench.repeat(
                    lambda p=p, b=backend: core.run_parallel(idx_td, p, backend=b,
                                                             chunksize=C.CHUNKSIZE),
                    args.reps, C.WARMUPS, label=f"{backend} p={p}")
                r = bench.summarize(runs, baseline_median=t1)
                r.update(section="D_backend", level=level, backend=backend)
                rec.add(r)
                print(f"  {level:<6s} {backend:<8s} p={p:<3d} T={r['time_median']:7.3f}s "
                      f"S={r['speedup']:5.2f}x E={r['efficiency']:6.1%}")

    # ------------------------------------------------------------------ E
    print("\n=== [E] parallelismo intra-immagine (thread interni di OpenCV) ===")
    n_e = min(1000, args.n)
    idx_e = list(range(n_e))
    for level in ("light", "heavy"):
        core.set_state(images=images, level=level, base_seed=C.BASE_SEED, return_mode="reduce")
        base = None
        for k in (1, 2, 4, 8, 14):
            cv2.setNumThreads(k if k > 1 else 0)
            runs = bench.repeat(lambda: core.run_sequential(idx_e), args.reps, C.WARMUPS,
                                label=f"cv2 threads={k}")
            r = bench.summarize(runs)
            base = base or r["time_median"]
            r.update(section="E_intra_image", level=level, cv2_threads=k,
                     speedup=base / r["time_median"], efficiency=base / r["time_median"] / k)
            rec.add(r)
            print(f"  {level:<6s} cv2_threads={k:<3d} T={r['time_median']:7.3f}s "
                  f"S_intra={r['speedup']:5.2f}x")
        cv2.setNumThreads(0)

    rec.save()
    print("\nNota: il CPU time totale (cpu_total_median) e' registrato in ogni riga e")
    print("permette il confronto wall-clock vs CPU richiesto dal requisito 15.")


if __name__ == "__main__":
    main()
