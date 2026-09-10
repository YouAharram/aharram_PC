from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import core, dataset, pipelines          # noqa: E402
from src.config import BASE_SEED, DATASET_SEED, RESULTS  # noqa: E402

import numpy as np                                # noqa: E402

N = 240
SIZE = 384
TARGET_LEVEL = "medium"

# pipeline con bbox/keypoint condivisa dai worker (creata lazily per processo)
_tgt_pipe: dict = {}


def augment_with_targets(indices):
    """Task che augmenta immagine + bounding box + keypoint."""
    t0 = time.perf_counter()
    pipe = _tgt_pipe.get("p")
    if pipe is None:
        pipe = _tgt_pipe["p"] = pipelines.build(TARGET_LEVEL, with_targets=True)
    images = core._STATE["images"]
    out = []
    for idx in indices:
        tgt = dataset.make_targets(idx, SIZE, base_seed=DATASET_SEED)
        pipe.set_random_seed(BASE_SEED + idx)
        res = pipe(image=images[idx], bboxes=tgt["bboxes"], labels=tgt["labels"],
                   keypoints=tgt["keypoints"])
        out.append((dataset.digest(res["image"]),
                    np.round(np.asarray(res["bboxes"], dtype=np.float64).reshape(-1, 4), 6).tolist(),
                    np.round(np.asarray(res["keypoints"], dtype=np.float64).reshape(-1, 2), 6).tolist()))
    import os
    return core.TaskResult(list(indices), out, os.getpid(), t0, time.perf_counter())


# RNG unico creato nel padre e quindi ereditato identico da tutti i figli forkati
_naive_pipe = pipelines.build("medium", seed=BASE_SEED)
_naive_pipe.save_applied_params = True


def _params_signature(applied) -> str:
    """Firma testuale dei parametri estratti a caso dalle trasformazioni."""
    parts = []
    for name, params in applied:
        vals = []
        for k, v in sorted(params.items()):
            if k == "shape":
                continue
            arr = np.asarray(v, dtype=object)
            vals.append(f"{k}={np.array2string(np.asarray(v).ravel(), precision=6)}"
                        if arr.dtype != object or np.ndim(v) else f"{k}={v}")
        parts.append(f"{name}({','.join(vals)})")
    return "|".join(parts)


def augment_naive(indices):
    """Seeding INGENUO: nessun reseed per immagine, RNG ereditato dal processo padre.

    Restituisce la *firma dei parametri* estratti a caso: e' li' che si vede la
    collisione, perche' immagini di input diverse danno comunque output diversi.
    """
    import os
    t0 = time.perf_counter()
    images = core._STATE["images"]
    out = []
    for idx in indices:
        res = _naive_pipe(image=images[idx])
        out.append(_params_signature(res["applied_transforms"]))
    return core.TaskResult(list(indices), out, os.getpid(), t0, time.perf_counter())


_seeded_pipe = pipelines.build("medium")
_seeded_pipe.save_applied_params = True


def augment_seeded_params(indices):
    """Stessa cosa ma con il reseed per immagine adottato nel progetto."""
    import os
    t0 = time.perf_counter()
    images = core._STATE["images"]
    out = []
    for idx in indices:
        _seeded_pipe.set_random_seed(BASE_SEED + idx)
        res = _seeded_pipe(image=images[idx])
        out.append(_params_signature(res["applied_transforms"]))
    return core.TaskResult(list(indices), out, os.getpid(), t0, time.perf_counter())


def as_map(run) -> dict[int, object]:
    return dict(run.payload)


def main() -> None:
    global N, SIZE
    ap = argparse.ArgumentParser(description="Verifica di equivalenza parallelo/sequenziale")
    ap.add_argument("--n", type=int, default=N, help="numero di immagini da verificare")
    ap.add_argument("--size", type=int, default=SIZE, help="lato delle immagini")
    args = ap.parse_args()
    N, SIZE = args.n, args.size

    print(__doc__)
    report: dict = {"n_images": N, "image_size": SIZE, "checks": {}}

    print(f"[setup] {N} immagini {SIZE}x{SIZE}")
    images = dataset.make_memory_dataset(N, SIZE, base_seed=DATASET_SEED)
    core.set_state(images=images, level="medium", base_seed=BASE_SEED, return_mode="digest")
    idx = list(range(N))

    # ---------------------------------------------------------------- A + B
    print("\n[A/B] output bit-identico e nessuna immagine persa/duplicata")
    ref = as_map(core.run_sequential(idx, keep_payload=True))
    assert len(ref) == N, "la baseline sequenziale non ha coperto tutte le immagini"
    report["reference_digest_sample"] = {str(k): ref[k] for k in list(ref)[:3]}

    configs = [
        ("process", 2, "dynamic", 1), ("process", 4, "dynamic", 7),
        ("process", 8, "dynamic", 16), ("process", 20, "dynamic", 64),
        ("process", 4, "static", None), ("process", 14, "static", None),
        ("thread", 8, "dynamic", 16),
    ]
    ab = []
    for backend, workers, sched, chunk in configs:
        run = core.run_parallel(idx, workers, backend=backend, scheduling=sched,
                                chunksize=chunk, keep_payload=True)
        got = run.payload
        seen = [i for i, _ in got]
        checks = {
            "config": f"{backend} p={workers} {sched} chunk={chunk}",
            "n_processed": len(seen),
            "all_present": sorted(seen) == idx,
            "no_duplicates": len(set(seen)) == len(seen),
            "bit_identical": all(ref[i] == d for i, d in got),
            "n_tasks": run.tasks,
        }
        ab.append(checks)
        flag = "OK " if all(v is True for v in list(checks.values())[2:5]) else "FALLITO"
        print(f"  {flag} {checks['config']:38s} img={checks['n_processed']} "
              f"task={run.tasks} identici={checks['bit_identical']}")
    report["checks"]["equivalence"] = ab

    # -------------------------------------------------------------------- C
    print("\n[C] coerenza di bounding box e keypoint")
    small = list(range(min(120, N)))
    seq_t = as_map(core.run_sequential(small, work=augment_with_targets, keep_payload=True))
    par_t = as_map(core.run_process_pool(small, 8, chunksize=5, work=augment_with_targets,
                                         keep_payload=True))
    same_img = sum(seq_t[i][0] == par_t[i][0] for i in small)
    same_box = sum(seq_t[i][1] == par_t[i][1] for i in small)
    same_kp = sum(seq_t[i][2] == par_t[i][2] for i in small)
    valid_box = all(x1 < x2 and y1 < y2 and 0 <= x1 and 0 <= y1
                    for i in small for x1, y1, x2, y2 in par_t[i][1])
    n_box = sum(len(par_t[i][1]) for i in small)
    n_kp = sum(len(par_t[i][2]) for i in small)
    print(f"  immagini identiche : {same_img}/{len(small)}")
    print(f"  bbox identiche     : {same_box}/{len(small)}  (totale {n_box} box, geometria valida: {valid_box})")
    print(f"  keypoint identici  : {same_kp}/{len(small)}  (totale {n_kp} keypoint)")
    report["checks"]["targets"] = {
        "images_identical": same_img, "bboxes_identical": same_box,
        "keypoints_identical": same_kp, "n_boxes": n_box, "n_keypoints": n_kp,
        "boxes_geometrically_valid": bool(valid_box), "n_images": len(small),
    }

    # -------------------------------------------------------------------- D
    print("\n[D] controprova: seeding ingenuo (RNG unico ereditato dal fork)")
    print("    confronto le *firme dei parametri* estratti a caso, non i pixel:")
    print("    input diversi danno output diversi anche quando la trasformazione e' la stessa.")
    naive_seq = as_map(core.run_sequential(idx, work=augment_naive, keep_payload=True))
    naive_par = as_map(core.run_process_pool(idx, 8, chunksize=16, work=augment_naive,
                                             keep_payload=True))
    seeded_seq = as_map(core.run_sequential(idx, work=augment_seeded_params, keep_payload=True))
    seeded_par = as_map(core.run_process_pool(idx, 8, chunksize=16, work=augment_seeded_params,
                                              keep_payload=True))
    uniq_naive_seq = len(set(naive_seq.values()))
    uniq_naive_par = len(set(naive_par.values()))
    uniq_seed_par = len(set(seeded_par.values()))
    match_naive = sum(naive_seq[i] == naive_par[i] for i in idx)
    match_seeded = sum(seeded_seq[i] == seeded_par[i] for i in idx)
    print(f"  ingenuo  - parametri distinti, sequenziale : {uniq_naive_seq}/{N}")
    print(f"  ingenuo  - parametri distinti, parallelo p=8: {uniq_naive_par}/{N}"
          f"   -> {N - uniq_naive_par} collisioni tra worker")
    print(f"  ingenuo  - parametri uguali al sequenziale  : {match_naive}/{N}")
    print(f"  adottato - parametri distinti, parallelo p=8: {uniq_seed_par}/{N}")
    print(f"  adottato - parametri uguali al sequenziale  : {match_seeded}/{N}")
    print("  => senza reseed per immagine i worker forkati condividono lo stato dell'RNG")
    print("     e riapplicano le stesse trasformazioni: l'augmentation perde diversita'")
    print("     e il risultato dipende dal numero di worker. Il seeding per indice adottato")
    print("     nel progetto elimina il problema (nessuna collisione, output riproducibile).")
    report["checks"]["naive_seeding"] = {
        "unique_params_sequential_naive": uniq_naive_seq,
        "unique_params_parallel_p8_naive": uniq_naive_par,
        "collisions_naive_p8": N - uniq_naive_par,
        "params_identical_to_sequential_naive": match_naive,
        "unique_params_parallel_p8_seeded": uniq_seed_par,
        "params_identical_to_sequential_seeded": match_seeded,
        "n_images": N,
    }

    ok = (all(c["all_present"] and c["no_duplicates"] and c["bit_identical"] for c in ab)
          and same_img == same_box == same_kp == len(small) and valid_box
          and match_seeded == N and uniq_seed_par == N)
    report["all_checks_passed"] = bool(ok)
    out = RESULTS / "01_correctness.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\n{'TUTTI I CONTROLLI SUPERATI' if ok else 'ALCUNI CONTROLLI SONO FALLITI'}")
    print(f"  -> salvato {out}")


if __name__ == "__main__":
    main()
