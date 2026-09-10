"""Harness di misura: warm-up, ripetizioni, statistiche e salvataggio CSV.

Requisiti 7, 8, 15: wall-clock time con `time.perf_counter`, almeno 5-10
ripetizioni per configurazione precedute da 1-2 warm-up scartati, statistiche
(mean/median/std/min/max + intervallo di confidenza al 95%), speedup,
efficienza, throughput e CPU time.
"""
from __future__ import annotations

import csv
import gc
import json
import math
import statistics as st
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

from .core import RunResult

# quantili t di Student a due code, 95%, per gradi di liberta' 1..30
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
        14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
        20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
        26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def t95(df: int) -> float:
    return _T95.get(df, 1.96)


@dataclass
class Stats:
    n: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    ci95: float          # semiampiezza dell'intervallo di confidenza sulla media

    @classmethod
    def of(cls, values: Iterable[float]) -> "Stats":
        v = [float(x) for x in values]
        n = len(v)
        mean = st.fmean(v)
        std = st.stdev(v) if n > 1 else 0.0
        ci = t95(n - 1) * std / math.sqrt(n) if n > 1 else 0.0
        return cls(n, mean, st.median(v), std, min(v), max(v), ci)

    def as_dict(self, prefix: str) -> dict:
        return {f"{prefix}_{k}": v for k, v in asdict(self).items() if k != "n"} | {f"{prefix}_n": self.n}


def repeat(factory: Callable[[], RunResult], reps: int = 7, warmups: int = 2,
           verbose: bool = True, label: str = "") -> list[RunResult]:
    """Esegue warm-up (scartati) + `reps` misurazioni valide."""
    for i in range(warmups):
        gc.collect()
        factory()
        if verbose:
            print(f"    warmup {i + 1}/{warmups}", end="\r", flush=True)
    runs = []
    for i in range(reps):
        gc.collect()
        r = factory()
        runs.append(r)
        if verbose:
            print(f"    {label} rep {i + 1}/{reps}: {r.wall_total:.3f}s "
                  f"({r.throughput:.1f} img/s)      ", end="\r", flush=True)
    if verbose:
        print(" " * 78, end="\r")
    return runs


def summarize(runs: list[RunResult], *, baseline_median: float | None = None, **extra) -> dict:
    """Aggrega le ripetizioni in una riga di risultati."""
    wall = Stats.of(r.wall_total for r in runs)
    comp = Stats.of(r.wall_compute for r in runs)
    setup = Stats.of(r.pool_setup for r in runs)
    cpu_main = Stats.of(r.cpu_main for r in runs)
    cpu_child = Stats.of(r.cpu_children for r in runs)
    cpu_tot = Stats.of(r.cpu_total for r in runs)
    thr = Stats.of(r.throughput for r in runs)
    imb = [r.imbalance for r in runs if r.imbalance == r.imbalance]  # esclude NaN

    r0 = runs[0]
    row = {
        "workers": r0.workers,
        "n_images": r0.n_images,
        "mode": r0.mode,
        "tasks": r0.tasks,
        "time_mean": wall.mean, "time_median": wall.median, "time_std": wall.std,
        "time_min": wall.min, "time_max": wall.max, "time_ci95": wall.ci95, "reps": wall.n,
        "compute_median": comp.median, "pool_setup_median": setup.median,
        "cpu_main_median": cpu_main.median, "cpu_children_median": cpu_child.median,
        "cpu_total_median": cpu_tot.median,
        "throughput_median": thr.median, "throughput_mean": thr.mean,
        "imbalance_median": st.median(imb) if imb else float("nan"),
        "task_count": r0.tasks,
    }
    if baseline_median:
        row["speedup"] = baseline_median / wall.median
        row["efficiency"] = row["speedup"] / max(r0.workers, 1)
        row["speedup_compute"] = baseline_median / comp.median
        # metrica di Karp-Flatt: frazione seriale stimata a posteriori da S e p,
        # e = (1/S - 1/p) / (1 - 1/p). Se cresce con p, l'overhead cresce con p
        # (non e' pura frazione seriale nel senso di Amdahl).
        p, s = r0.workers, row["speedup"]
        row["amdahl_serial_fraction"] = ((p / s) - 1) / (p - 1) if p > 1 and s > 0 else float("nan")
        row["cpu_overhead_ratio"] = row["cpu_total_median"] / baseline_median if baseline_median else float("nan")
    row.update(extra)
    return row


class Recorder:
    """Accumula righe di risultati e le salva in CSV + JSON."""

    def __init__(self, name: str, results_dir: str | Path = "results"):
        self.name = name
        self.dir = Path(results_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.rows: list[dict] = []
        self.meta: dict = {"experiment": name, "started": time.strftime("%Y-%m-%d %H:%M:%S")}

    def add(self, row: dict) -> dict:
        self.rows.append(row)
        return row

    def save(self) -> Path:
        if not self.rows:
            raise RuntimeError("nessuna riga da salvare")
        keys: list[str] = []
        for r in self.rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        csv_path = self.dir / f"{self.name}.csv"
        with csv_path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            for r in self.rows:
                w.writerow({k: r.get(k, "") for k in keys})
        self.meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        (self.dir / f"{self.name}_meta.json").write_text(json.dumps(self.meta, indent=2, default=str))
        print(f"  -> salvato {csv_path}")
        return csv_path


def print_table(rows: list[dict], cols: list[tuple[str, str, str]]) -> None:
    """Stampa una tabella allineata: cols = [(chiave, intestazione, formato)]."""
    header = " | ".join(f"{h:>{max(len(h), 9)}}" for _, h, _ in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        cells = []
        for key, h, fmt in cols:
            v = r.get(key, "")
            try:
                cells.append(f"{format(v, fmt):>{max(len(h), 9)}}")
            except (ValueError, TypeError):
                cells.append(f"{str(v):>{max(len(h), 9)}}")
        print(" | ".join(cells))
