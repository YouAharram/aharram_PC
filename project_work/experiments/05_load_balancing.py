from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import bench, core, dataset, sysinfo   # noqa: E402
from src import config as C                     # noqa: E402


def worker_profile(runs) -> dict:
    """Statistiche sui tempi occupati dai singoli worker (run mediano)."""
    mid = sorted(runs, key=lambda r: r.wall_total)[len(runs) // 2]
    busy = sorted(mid.worker_busy.values(), reverse=True)
    if not busy:
        return {}
    return {"busy_max": max(busy), "busy_min": min(busy), "busy_mean": st.fmean(busy),
            "busy_spread": max(busy) - min(busy),
            "busy_profile": ";".join(f"{b:.3f}" for b in busy)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="medium")
    ap.add_argument("--n", type=int, default=C.HETERO_N)
    ap.add_argument("--reps", type=int, default=C.REPS)
    ap.add_argument("--workers", nargs="+", type=int, default=C.HETERO_WORKERS)
    args = ap.parse_args()

    rec = bench.Recorder("05_load_balancing", C.RESULTS)
    rec.meta.update(system=sysinfo.collect(), n_images=args.n, level=args.level,
                    sizes=C.HETERO_SIZES, weights=C.HETERO_WEIGHTS, reps=args.reps,
                    warmups=C.WARMUPS, workers=args.workers, resize_last=True)

    for order, shuffle_seed in (("sorted", None), ("shuffled", 99)):
        print(f"\n########## dataset '{order}' ##########")
        images = dataset.make_heterogeneous_dataset(
            args.n, C.HETERO_SIZES, C.HETERO_WEIGHTS,
            base_seed=C.DATASET_SEED, shuffle_seed=shuffle_seed)
        sizes = [im.shape[0] for im in images]
        counts = {s: sizes.count(s) for s in sorted(set(sizes))}
        print(f"  {args.n} immagini, distribuzione dei lati: {counts}")
        print(f"  {dataset.dataset_bytes(images) / 1024**2:.0f} MB in RAM")

        core.set_state(images=images, level=args.level, base_seed=C.BASE_SEED,
                       return_mode="reduce", resize_last=True)
        idx = list(range(args.n))

        seq = bench.repeat(lambda: core.run_sequential(idx), args.reps, C.WARMUPS, label="seq")
        t1 = bench.summarize(seq)["time_median"]
        row = bench.summarize(seq, baseline_median=t1)
        row.update(order=order, strategy="sequential", chunksize="-")
        rec.add(row)
        print(f"  T1 = {t1:.3f}s ({t1 / args.n * 1000:.2f} ms/img in media)")

        strategies = [("static", "static", None)] + \
                     [(f"dynamic({k})", "dynamic", k) for k in (1, 8, 32, 128)]
        for p in args.workers:
            print(f"\n  -- p = {p} worker --")
            for name, sched, chunk in strategies:
                runs = bench.repeat(
                    lambda p=p, sched=sched, chunk=chunk:
                        core.run_process_pool(idx, p, scheduling=sched, chunksize=chunk),
                    args.reps, C.WARMUPS, label=name)
                r = bench.summarize(runs, baseline_median=t1)
                r.update(order=order, strategy=name, scheduling=sched,
                         chunksize=chunk if chunk is not None else "-",
                         **worker_profile(runs))
                rec.add(r)
                print(f"    {name:<12s} task={r['task_count']:<5d} T={r['time_median']:7.3f}s  "
                      f"S={r['speedup']:5.2f}x E={r['efficiency']:6.1%}  "
                      f"imbalance={r['imbalance_median']:.3f}  "
                      f"busy max/min={r.get('busy_max', 0):.2f}/{r.get('busy_min', 0):.2f}s")

            rows = [x for x in rec.rows if x.get("order") == order and x["workers"] == p
                    and x["strategy"] != "sequential"]
            stat = next(x for x in rows if x["strategy"] == "static")
            best_dyn = min((x for x in rows if x["strategy"].startswith("dynamic")),
                           key=lambda x: x["time_median"])
            gain = stat["time_median"] / best_dyn["time_median"] - 1
            print(f"    => dinamico ({best_dyn['strategy']}) piu' veloce dello statico del {gain:.1%}")

    rec.save()


if __name__ == "__main__":
    main()
