#!/usr/bin/env python
"""Esperimento 4 - Dimensione dei task/chunk (requisito 13).

Con il numero di worker fissato si varia la granularita' dei task, cioe' quante
immagini vengono assegnate a un worker per ogni dispatch.

Trade-off atteso:
  chunk piccolo -> bilanciamento migliore, ma un dispatch (e una serializzazione
                   del risultato) ogni pochissime immagini: overhead di scheduling;
  chunk grande  -> overhead minimo, ma la "coda" finale e' sbilanciata perche'
                   l'ultimo worker puo' restare da solo a lavorare a lungo.
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
    ap.add_argument("--workers", nargs="+", type=int, default=[C.PHYSICAL_CORES, C.LOGICAL_CORES])
    ap.add_argument("--n", type=int, default=C.N_IMAGES)
    ap.add_argument("--reps", type=int, default=C.REPS)
    ap.add_argument("--chunks", nargs="+", type=int, default=C.CHUNK_SIZES)
    args = ap.parse_args()

    rec = bench.Recorder("04_chunk_size", C.RESULTS)
    rec.meta.update(system=sysinfo.collect(), n_images=args.n, reps=args.reps,
                    warmups=C.WARMUPS, workers=args.workers, chunks=args.chunks)

    images = dataset.load_or_make(args.n, C.IMAGE_SIZE, cache_dir=C.CACHE, base_seed=C.DATASET_SEED)
    idx = list(range(args.n))

    for level in args.levels:
        core.set_state(images=images, level=level, base_seed=C.BASE_SEED, return_mode="reduce")
        seq = bench.repeat(lambda: core.run_sequential(idx), args.reps, C.WARMUPS, label="seq")
        t1 = bench.summarize(seq)["time_median"]
        row = bench.summarize(seq, baseline_median=t1)
        row.update(level=level, backend="sequential", chunksize="-")
        rec.add(row)
        print(f"\n=== chunk size, workload '{level}' (T1 = {t1:.3f}s) ===")

        for p in args.workers:
            print(f"  -- p = {p} worker --")
            for ch in args.chunks:
                if ch > args.n:
                    continue
                runs = bench.repeat(
                    lambda p=p, ch=ch: core.run_process_pool(idx, p, scheduling="dynamic",
                                                             chunksize=ch),
                    args.reps, C.WARMUPS, label=f"chunk={ch}")
                r = bench.summarize(runs, baseline_median=t1)
                r.update(level=level, backend="process", chunksize=ch,
                         scheduling="dynamic",
                         tasks_per_worker=r["task_count"] / p)
                rec.add(r)
                print(f"    chunk={ch:<5d} task={r['task_count']:<5d} "
                      f"({r['tasks_per_worker']:6.1f}/worker) T={r['time_median']:7.3f}s "
                      f"S={r['speedup']:6.2f}x  imb={r['imbalance_median']:.3f}")

            rows = [r for r in rec.rows
                    if r["level"] == level and r["backend"] == "process" and r["workers"] == p]
            best = min(rows, key=lambda r: r["time_median"])
            worst = max(rows, key=lambda r: r["time_median"])
            print(f"    => migliore chunk={best['chunksize']} ({best['time_median']:.3f}s), "
                  f"peggiore chunk={worst['chunksize']} ({worst['time_median']:.3f}s), "
                  f"divario {worst['time_median'] / best['time_median'] - 1:.1%}")

    rec.save()


if __name__ == "__main__":
    main()
