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
    ap.add_argument("--n", type=int, default=C.N_IMAGES)
    ap.add_argument("--reps", type=int, default=C.REPS)
    ap.add_argument("--workers", nargs="+", type=int, default=C.WORKERS)
    args = ap.parse_args()

    rec = bench.Recorder("02_strong_scaling", C.RESULTS)
    rec.meta.update(system=sysinfo.collect(), n_images=args.n, image_size=C.IMAGE_SIZE,
                    reps=args.reps, warmups=C.WARMUPS, chunksize=C.CHUNKSIZE,
                    workers=args.workers, scheduling="dynamic", backend="process",
                    start_method="fork", return_mode="reduce")

    print(f"[setup] dataset: {args.n} immagini {C.IMAGE_SIZE}x{C.IMAGE_SIZE}")
    images = dataset.load_or_make(args.n, C.IMAGE_SIZE, cache_dir=C.CACHE, base_seed=C.DATASET_SEED)
    print(f"  {dataset.dataset_bytes(images) / 1024**3:.2f} GB in RAM, "
          f"condivisi con i worker in copy-on-write (fork)")
    idx = list(range(args.n))

    for level in args.levels:
        print(f"\n=== workload '{level}' : {', '.join(pipelines.describe(level))} ===")
        core.set_state(images=images, level=level, base_seed=C.BASE_SEED, return_mode="reduce")

        print("  [T1] baseline sequenziale")
        seq = bench.repeat(lambda: core.run_sequential(idx), args.reps, C.WARMUPS, label="seq")
        base = bench.summarize(seq, baseline_median=None)
        t1 = base["time_median"]
        base.update(bench.summarize(seq, baseline_median=t1))
        base.update(level=level, backend="sequential", scheduling="-", chunksize="-",
                    ms_per_image=t1 / args.n * 1000)
        rec.add(base)
        print(f"    T1 = {t1:.3f}s  ({t1 / args.n * 1000:.2f} ms/img, "
              f"{args.n / t1:.0f} img/s)  std={base['time_std'] * 1000:.0f}ms")

        for p in args.workers:
            runs = bench.repeat(
                lambda p=p: core.run_process_pool(idx, p, scheduling="dynamic",
                                                  chunksize=C.CHUNKSIZE),
                args.reps, C.WARMUPS, label=f"p={p}")
            row = bench.summarize(runs, baseline_median=t1)
            row.update(level=level, backend="process", scheduling="dynamic",
                       chunksize=C.CHUNKSIZE, ms_per_image=row["time_median"] / args.n * 1000)
            rec.add(row)
            print(f"    p={p:<3d} T={row['time_median']:7.3f}s  S={row['speedup']:6.2f}x  "
                  f"E={row['efficiency'] * 100:5.1f}%  {row['throughput_median']:8.1f} img/s  "
                  f"CPU_tot={row['cpu_total_median']:7.2f}s  setup={row['pool_setup_median'] * 1000:5.1f}ms")

        rows = [r for r in rec.rows if r["level"] == level and r["backend"] == "process"]
        print(f"\n  --- tabella benchmark '{level}' ---")
        bench.print_table(rows, [("workers", "Workers", "d"), ("time_median", "Time[s]", ".3f"),
                                 ("time_std", "Std[s]", ".4f"), ("time_ci95", "CI95[s]", ".4f"),
                                 ("speedup", "Speedup", ".2f"), ("efficiency", "Effic.", ".1%"),
                                 ("throughput_median", "img/s", ".1f")])

    rec.save()


if __name__ == "__main__":
    main()
