from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import bench, core, dataset, sysinfo   # noqa: E402
from src import config as C                     # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="medium")
    ap.add_argument("--n", type=int, default=C.E2E_N)
    ap.add_argument("--reps", type=int, default=C.E2E_REPS)
    ap.add_argument("--workers", nargs="+", type=int, default=C.E2E_WORKERS)
    args = ap.parse_args()

    rec = bench.Recorder("06_end_to_end", C.RESULTS)
    rec.meta.update(system=sysinfo.collect(), n_images=args.n, level=args.level,
                    reps=args.reps, warmups=C.WARMUPS, workers=args.workers,
                    image_size=C.IMAGE_SIZE, jpeg_quality=92)

    print(f"[setup] preparo {args.n} JPEG in {C.E2E_IN}")
    paths = dataset.make_disk_dataset(C.E2E_IN, args.n, C.IMAGE_SIZE, base_seed=C.DATASET_SEED)
    in_mb = sum(p.stat().st_size for p in paths) / 1024**2
    print(f"  {in_mb:.1f} MB di input ({in_mb / args.n * 1024:.0f} KB/immagine)")
    C.E2E_OUT.mkdir(parents=True, exist_ok=True)
    idx = list(range(args.n))

    # ---- riferimento: solo calcolo, stesse immagini gia' in RAM ----------------
    print("\n[A] solo calcolo (immagini gia' in RAM)")
    images = [dataset.make_image(i, C.IMAGE_SIZE, base_seed=C.DATASET_SEED) for i in range(args.n)]
    core.set_state(images=images, level=args.level, base_seed=C.BASE_SEED, return_mode="reduce")
    seq_c = bench.repeat(lambda: core.run_sequential(idx), args.reps, C.WARMUPS, label="seq-comp")
    t1_c = bench.summarize(seq_c)["time_median"]
    row = bench.summarize(seq_c, baseline_median=t1_c)
    row.update(pipeline_scope="compute", backend="sequential")
    rec.add(row)
    print(f"  T1_compute = {t1_c:.3f}s ({t1_c / args.n * 1000:.2f} ms/img)")

    for p in args.workers:
        runs = bench.repeat(lambda p=p: core.run_process_pool(idx, p, chunksize=C.CHUNKSIZE),
                            args.reps, C.WARMUPS, label=f"comp p={p}")
        r = bench.summarize(runs, baseline_median=t1_c)
        r.update(pipeline_scope="compute", backend="process")
        rec.add(r)
        print(f"  p={p:<3d} T={r['time_median']:7.3f}s S={r['speedup']:5.2f}x "
              f"{r['throughput_median']:7.1f} img/s")
    del images

    # ---- pipeline completa ----------------------------------------------------
    print("\n[B] end-to-end (lettura da disco + augmentation + scrittura su disco)")
    core.set_state(images=None, paths=[str(p) for p in paths], out_dir=str(C.E2E_OUT),
                   level=args.level, base_seed=C.BASE_SEED)
    seq_e = bench.repeat(lambda: core.run_sequential(idx, work=core.augment_chunk_e2e),
                         args.reps, C.WARMUPS, label="seq-e2e")
    t1_e = bench.summarize(seq_e)["time_median"]
    row = bench.summarize(seq_e, baseline_median=t1_e)
    row.update(pipeline_scope="end_to_end", backend="sequential",
               io_fraction=1 - t1_c / t1_e)
    rec.add(row)
    out_mb = sum(p.stat().st_size for p in C.E2E_OUT.glob("*.jpg")) / 1024**2
    print(f"  T1_e2e = {t1_e:.3f}s ({t1_e / args.n * 1000:.2f} ms/img), output {out_mb:.1f} MB")
    print(f"  frazione di tempo NON dovuta al calcolo: {(1 - t1_c / t1_e):.1%}")

    for p in args.workers:
        runs = bench.repeat(
            lambda p=p: core.run_process_pool(idx, p, chunksize=C.CHUNKSIZE,
                                              work=core.augment_chunk_e2e),
            args.reps, C.WARMUPS, label=f"e2e p={p}")
        r = bench.summarize(runs, baseline_median=t1_e)
        r.update(pipeline_scope="end_to_end", backend="process")
        rec.add(r)
        print(f"  p={p:<3d} T={r['time_median']:7.3f}s S={r['speedup']:5.2f}x "
              f"E={r['efficiency']:6.1%} {r['throughput_median']:7.1f} img/s")

    comp = [r for r in rec.rows if r["pipeline_scope"] == "compute" and r["backend"] == "process"]
    e2e = [r for r in rec.rows if r["pipeline_scope"] == "end_to_end" and r["backend"] == "process"]
    print(f"\n  speedup massimo   solo calcolo : {max(r['speedup'] for r in comp):.2f}x")
    print(f"  speedup massimo   end-to-end   : {max(r['speedup'] for r in e2e):.2f}x")
    rec.save()
    shutil.rmtree(C.E2E_OUT, ignore_errors=True)


if __name__ == "__main__":
    main()
