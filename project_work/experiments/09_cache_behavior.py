from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import bench, core, dataset, sysinfo   # noqa: E402
from src import config as C                     # noqa: E402

SIZES = [128, 192, 256, 384, 512, 768, 1024]
TOTAL_PIXELS = 1500 * 512 * 512   # lavoro totale costante


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="medium")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--workers", nargs="+", type=int, default=[4, 14])
    ap.add_argument("--sizes", nargs="+", type=int, default=SIZES)
    ap.add_argument("--total-pixels", type=float, default=TOTAL_PIXELS,
                    help="pixel totali elaborati per configurazione (il lavoro resta costante)")
    args = ap.parse_args()
    total_pixels = int(args.total_pixels)

    rec = bench.Recorder("09_cache_behavior", C.RESULTS)
    info = sysinfo.collect()
    rec.meta.update(system=info, level=args.level, total_pixels=total_pixels,
                    reps=args.reps, workers=args.workers, sizes=args.sizes,
                    resize_last=True)
    print(f"L3 disponibile: {info.get('l3_cache')}   L2: {info.get('l2_cache')}")
    print(f"Lavoro totale costante: {total_pixels / 1e6:.0f} Mpixel per configurazione\n")

    for size in args.sizes:
        n = max(args.workers[-1] * 4, round(total_pixels / (size * size)))
        images = dataset.make_memory_dataset(n, size, base_seed=C.DATASET_SEED)
        ws_kb = size * size * 3 / 1024
        core.set_state(images=images, level=args.level, base_seed=C.BASE_SEED,
                       return_mode="reduce", resize_last=True)
        idx = list(range(n))

        seq = bench.repeat(lambda: core.run_sequential(idx), args.reps, C.WARMUPS, label="seq")
        t1 = bench.summarize(seq)["time_median"]
        mpix = n * size * size / 1e6
        row = bench.summarize(seq, baseline_median=t1)
        row.update(section="cache", image_size=size, working_set_kb=ws_kb, backend="sequential",
                   megapixels=mpix, ns_per_pixel=t1 / (mpix * 1e6) * 1e9)
        rec.add(row)
        print(f"size={size:<5d} N={n:<6d} working set/immagine={ws_kb / 1024:6.2f} MB  "
              f"T1={t1:6.3f}s  {row['ns_per_pixel']:6.2f} ns/pixel")

        for p in args.workers:
            runs = bench.repeat(lambda p=p: core.run_process_pool(idx, p, chunksize=C.CHUNKSIZE),
                                args.reps, C.WARMUPS, label=f"p={p}")
            r = bench.summarize(runs, baseline_median=t1)
            r.update(section="cache", image_size=size, working_set_kb=ws_kb, backend="process",
                     megapixels=mpix, ns_per_pixel=r["time_median"] / (mpix * 1e6) * 1e9,
                     aggregate_working_set_mb=ws_kb * p / 1024)
            rec.add(r)
            print(f"        p={p:<3d} T={r['time_median']:6.3f}s S={r['speedup']:5.2f}x "
                  f"E={r['efficiency']:6.1%}  working set aggregato={ws_kb * p / 1024:7.2f} MB")
        del images

    print("\n--- riepilogo: efficienza parallela in funzione del working set ---")
    for p in args.workers:
        rows = [r for r in rec.rows if r.get("backend") == "process" and r["workers"] == p]
        best = max(rows, key=lambda r: r["efficiency"])
        worst = min(rows, key=lambda r: r["efficiency"])
        print(f"  p={p}: efficienza migliore {best['efficiency']:.1%} a "
              f"{int(best['image_size'])}px ({best['aggregate_working_set_mb']:.1f} MB aggregati), "
              f"peggiore {worst['efficiency']:.1%} a {int(worst['image_size'])}px "
              f"({worst['aggregate_working_set_mb']:.1f} MB)")
    rec.save()


if __name__ == "__main__":
    main()
