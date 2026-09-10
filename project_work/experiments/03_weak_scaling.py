#!/usr/bin/env python
"""Esperimento 3 - Weak scaling (requisito 11).

Il carico per worker resta costante (WEAK_PER_WORKER immagini) mentre crescono
insieme problema e risorse: p worker elaborano p * WEAK_PER_WORKER immagini.

Nel caso ideale il tempo di esecuzione resta piatto. Le metriche riportate sono:
  * weak efficiency  E_w(p) = T(1, n1) / T(p, p*n1)
  * scaled speedup   S_w(p) = p * E_w(p)      (legge di Gustafson)

Nota sul dataset: per non richiedere 20 x 500 immagini in RAM, gli indici oltre
la dimensione del pool ricircolano (i % len(pool)). Il pool (2.36 GB) e' ordini
di grandezza piu' grande della cache L3 (24 MB), quindi il ricircolo non
introduce vantaggi di cache apprezzabili; il seed resta legato all'indice.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import bench, core, dataset, pipelines, sysinfo   # noqa: E402
from src import config as C                                # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", nargs="+", default=list(pipelines.LEVELS))
    ap.add_argument("--per-worker", type=int, default=C.WEAK_PER_WORKER)
    ap.add_argument("--reps", type=int, default=C.REPS)
    ap.add_argument("--workers", nargs="+", type=int, default=C.WEAK_WORKERS)
    args = ap.parse_args()

    rec = bench.Recorder("03_weak_scaling", C.RESULTS)
    rec.meta.update(system=sysinfo.collect(), per_worker=args.per_worker,
                    image_size=C.IMAGE_SIZE, reps=args.reps, warmups=C.WARMUPS,
                    chunksize=C.CHUNKSIZE, workers=args.workers, pool_size=C.N_IMAGES)

    print(f"[setup] pool di {C.N_IMAGES} immagini {C.IMAGE_SIZE}x{C.IMAGE_SIZE}")
    images = dataset.load_or_make(C.N_IMAGES, C.IMAGE_SIZE, cache_dir=C.CACHE,
                                  base_seed=C.DATASET_SEED)
    pool_n = len(images)

    for level in args.levels:
        print(f"\n=== weak scaling, workload '{level}' "
              f"({args.per_worker} immagini per worker) ===")
        core.set_state(images=images, level=level, base_seed=C.BASE_SEED, return_mode="reduce")

        base_idx = [i % pool_n for i in range(args.per_worker)]
        seq = bench.repeat(lambda: core.run_sequential(base_idx), args.reps, C.WARMUPS, label="seq")
        t1 = bench.summarize(seq)["time_median"]
        row = bench.summarize(seq, baseline_median=t1)
        row.update(level=level, backend="sequential", per_worker=args.per_worker,
                   weak_efficiency=1.0, scaled_speedup=1.0)
        rec.add(row)
        print(f"  T(1, {args.per_worker} img) = {t1:.3f}s   "
              f"({t1 / args.per_worker * 1000:.2f} ms/img)")

        for p in args.workers:
            n_p = args.per_worker * p
            idx = [i % pool_n for i in range(n_p)]
            runs = bench.repeat(
                lambda p=p, idx=idx: core.run_process_pool(idx, p, scheduling="dynamic",
                                                           chunksize=C.CHUNKSIZE),
                args.reps, C.WARMUPS, label=f"p={p}")
            r = bench.summarize(runs, baseline_median=t1)
            r["weak_efficiency"] = t1 / r["time_median"]
            r["scaled_speedup"] = p * r["weak_efficiency"]
            r.update(level=level, backend="process", per_worker=args.per_worker,
                     chunksize=C.CHUNKSIZE, scheduling="dynamic")
            rec.add(r)
            print(f"  p={p:<3d} n={n_p:<6d} T={r['time_median']:7.3f}s  "
                  f"E_weak={r['weak_efficiency'] * 100:5.1f}%  "
                  f"S_scaled={r['scaled_speedup']:5.2f}  "
                  f"{r['throughput_median']:8.1f} img/s")

        rows = [r for r in rec.rows if r["level"] == level and r["backend"] == "process"]
        print(f"\n  --- weak scaling '{level}' ---")
        bench.print_table(rows, [("workers", "Workers", "d"), ("n_images", "N img", "d"),
                                 ("time_median", "Time[s]", ".3f"), ("time_std", "Std[s]", ".4f"),
                                 ("weak_efficiency", "E_weak", ".1%"),
                                 ("scaled_speedup", "S_scaled", ".2f"),
                                 ("throughput_median", "img/s", ".1f")])

    rec.save()


if __name__ == "__main__":
    main()
