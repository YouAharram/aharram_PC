#!/usr/bin/env python
"""Esperimento 8 - Perche' lo speedup satura: analisi fisica della macchina (requisito 17).

Gli esperimenti precedenti misurano *quanto* si scala. Questo misura *perche'*
non si scala di piu', sulla CPU specifica usata (Intel i7-1280P, architettura
ibrida: 6 P-core con SMT + 8 E-core, 20 thread logici, portatile con budget
termico limitato).

  A. caratterizzazione dei core: stesso lavoro fissato su un P-core e su un
     E-core -> rapporto di prestazioni reale tra i due tipi di core;
  B. frequenza e temperatura in funzione del numero di worker: quanto la
     frequenza cala passando da 1 core attivo a tutti i core attivi;
  C. scaling con affinita' forzata: solo P-core fisici / P-core con SMT /
     solo E-core / tutti -> quantifica separatamente il guadagno dell'SMT e il
     contributo degli E-core;
  D. modello predittivo dello speedup massimo raggiungibile e confronto con la
     misura: la differenza residua e' la contesa sulle risorse condivise;
  E. throttling termico su una corsa sostenuta.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import bench, core, dataset, monitor, sysinfo   # noqa: E402
from src import config as C                              # noqa: E402

ALL_CPUS = set(range(os.cpu_count() or 1))


def with_affinity(cpus: set[int], fn):
    """Esegue `fn` con l'affinita' del processo (ereditata dai figli) limitata a `cpus`."""
    old = os.sched_getaffinity(0)
    os.sched_setaffinity(0, cpus)
    try:
        return fn()
    finally:
        os.sched_setaffinity(0, old)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="heavy")
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--sustained", type=float, default=60.0)
    args = ap.parse_args()

    cores = monitor.classify_cores()
    p_phys = monitor.physical_performance_cores()
    print(f"P-core logici: {cores['performance']}  (fisici: {p_phys})")
    print(f"E-core       : {cores['efficiency']}")

    rec = bench.Recorder("08_saturation", C.RESULTS)
    rec.meta.update(system=sysinfo.collect(), level=args.level, n_images=args.n,
                    reps=args.reps, cores=cores, physical_p_cores=p_phys)

    images = dataset.load_or_make(args.n, C.IMAGE_SIZE, cache_dir=C.CACHE, base_seed=C.DATASET_SEED)
    core.set_state(images=images, level=args.level, base_seed=C.BASE_SEED, return_mode="reduce")
    idx = list(range(args.n))

    # ---------------------------------------------------------------------- A
    print("\n=== [A] un P-core contro un E-core (stesso lavoro, 1 worker) ===")
    core_times = {}
    for name, cpu in (("P-core", p_phys[0]), ("E-core", cores["efficiency"][0])):
        with monitor.Sampler(0.05) as smp:
            runs = with_affinity({cpu}, lambda: bench.repeat(
                lambda: core.run_sequential(idx), args.reps, 1, label=name))
        r = bench.summarize(runs)
        r.update(section="A_core_type", core_type=name, cpu=cpu, **smp.summary())
        rec.add(r)
        core_times[name] = r["time_median"]
        sm = smp.summary()
        freq = sm.get("freq_p_busy_mhz" if name == "P-core" else "freq_e_busy_mhz") or 0.0
        print(f"  {name}: T={r['time_median']:.3f}s  {r['throughput_median']:.1f} img/s  "
              f"f={freq:.0f} MHz temp={sm.get('temp_max_c')}C")
    r_e = core_times["P-core"] / core_times["E-core"]
    print(f"  => un E-core vale {r_e:.2f} P-core su questo workload")
    rec.meta["e_core_relative_throughput"] = r_e

    # ---------------------------------------------------------------------- B
    print("\n=== [B] frequenza e temperatura in funzione del numero di worker ===")
    seq = bench.repeat(lambda: core.run_sequential(idx), args.reps, C.WARMUPS, label="seq")
    t1 = bench.summarize(seq)["time_median"]
    for p in [1, 2, 4, 6, 8, 12, 14, 20]:
        with monitor.Sampler(0.1) as smp:
            runs = bench.repeat(lambda p=p: core.run_process_pool(idx, p, chunksize=C.CHUNKSIZE),
                                args.reps, C.WARMUPS, label=f"p={p}")
        s = smp.summary()
        r = bench.summarize(runs, baseline_median=t1)
        r.update(section="B_frequency", **s)
        rec.add(r)
        print(f"  p={p:<3d} T={r['time_median']:6.3f}s S={r['speedup']:5.2f}x  "
              f"f_P={s.get('freq_p_busy_mhz') or 0:.0f} MHz  f_E={s.get('freq_e_busy_mhz') or 0:.0f} MHz  "
              f"T_max={s.get('temp_max_c')}C")

    b_rows = [x for x in rec.rows if x.get("section") == "B_frequency"]
    fmax = max((x.get("freq_p_busy_mhz") or 0) for x in b_rows)
    fmin = min((x.get("freq_p_busy_mhz") or 0) for x in b_rows if x["workers"] >= 14)
    print(f"  => frequenza dei P-core: {fmax:.0f} MHz con 1 worker -> {fmin:.0f} MHz a pieno carico "
          f"({fmin / fmax - 1:+.1%})")
    rec.meta["freq_drop_ratio"] = fmin / fmax if fmax else None

    # ---------------------------------------------------------------------- C
    print("\n=== [C] scaling con affinita' forzata ===")
    configs = [
        ("1 P-core", {p_phys[0]}, 1),
        ("P-core fisici", set(p_phys), len(p_phys)),
        ("P-core + SMT", set(cores["performance"]), len(cores["performance"])),
        ("solo E-core", set(cores["efficiency"]), len(cores["efficiency"])),
        ("tutti i core", ALL_CPUS, len(ALL_CPUS)),
        ("tutti (p=14)", ALL_CPUS, 14),
    ]
    thr = {}
    for name, cpus, p in configs:
        with monitor.Sampler(0.1) as smp:
            runs = with_affinity(cpus, lambda p=p: bench.repeat(
                lambda: core.run_process_pool(idx, p, chunksize=C.CHUNKSIZE),
                args.reps, C.WARMUPS, label=name))
        r = bench.summarize(runs, baseline_median=t1)
        r.update(section="C_affinity", affinity=name, n_cpus=len(cpus), **smp.summary())
        rec.add(r)
        thr[name] = r["throughput_median"]
        print(f"  {name:<15s} p={p:<3d} cpus={len(cpus):<3d} T={r['time_median']:6.3f}s "
              f"S={r['speedup']:5.2f}x  {r['throughput_median']:7.1f} img/s")

    smt_gain = thr["P-core + SMT"] / thr["P-core fisici"] - 1
    print(f"  => guadagno dell'SMT sui P-core: {smt_gain:+.1%}")
    print(f"  => throughput degli 8 E-core = {thr['solo E-core'] / thr['P-core fisici']:.2f}x "
          f"quello dei 6 P-core fisici")

    # ---------------------------------------------------------------------- D
    print("\n=== [D] modello predittivo dello speedup massimo ===")
    predicted = (thr["P-core + SMT"] + thr["solo E-core"]) / thr["1 P-core"]
    measured = thr["tutti i core"] / thr["1 P-core"]
    print(f"  somma dei sottoinsiemi misurati separatamente : S_pred = {predicted:.2f}x")
    print(f"  misura con tutti i core insieme              : S_mis  = {measured:.2f}x")
    print(f"  perdita per contesa su risorse condivise      : {1 - measured / predicted:.1%}")
    print(f"  (memoria/L3 condivisa, budget di potenza, scheduling)")
    rec.meta["model"] = {"predicted_speedup": predicted, "measured_speedup": measured,
                         "contention_loss": 1 - measured / predicted,
                         "smt_gain": smt_gain,
                         "ecore_vs_pcore_throughput": thr["solo E-core"] / thr["P-core fisici"]}

    # ---------------------------------------------------------------------- E
    print(f"\n=== [E] throttling termico su {args.sustained:.0f}s di carico sostenuto (p=14) ===")
    timeline = []
    with monitor.Sampler(0.25) as smp:
        t_end = time.perf_counter() + args.sustained
        n_batch = 0
        while time.perf_counter() < t_end:
            core.run_process_pool(idx, 14, chunksize=C.CHUNKSIZE)
            n_batch += 1
        timeline = smp.timeline()
    s = smp.summary()
    first = [f for t, f, _ in timeline if t < args.sustained * 0.15 and f > 0]
    last = [f for t, f, _ in timeline if t > args.sustained * 0.85 and f > 0]
    import statistics as st
    print(f"  {n_batch} batch da {args.n} immagini")
    print(f"  frequenza media primi 15%: {st.fmean(first):.0f} MHz")
    print(f"  frequenza media ultimi 15%: {st.fmean(last):.0f} MHz "
          f"({st.fmean(last) / st.fmean(first) - 1:+.1%})")
    print(f"  temperatura max: {s.get('temp_max_c')}C")
    (C.RESULTS / "08_thermal_timeline.json").write_text(json.dumps(
        {"sustained_s": args.sustained, "workers": 14, "batches": n_batch,
         "freq_start_mhz": st.fmean(first), "freq_end_mhz": st.fmean(last),
         "timeline": [{"t": t, "freq_mhz": f, "temp_c": c} for t, f, c in timeline]}, indent=2))
    rec.meta["thermal"] = {"freq_start_mhz": st.fmean(first), "freq_end_mhz": st.fmean(last),
                           "drop": st.fmean(last) / st.fmean(first) - 1,
                           "temp_max_c": s.get("temp_max_c")}
    rec.save()


if __name__ == "__main__":
    main()
