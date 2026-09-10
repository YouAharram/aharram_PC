from __future__ import annotations

import os
import statistics as st
import threading
import time
from pathlib import Path

CPU_DIR = Path("/sys/devices/system/cpu")


def cpu_max_freqs() -> dict[int, int]:
    out = {}
    for cpu in sorted(CPU_DIR.glob("cpu[0-9]*")):
        f = cpu / "cpufreq" / "cpuinfo_max_freq"
        if f.exists():
            out[int(cpu.name[3:])] = int(f.read_text())
    return out


def classify_cores() -> dict[str, list[int]]:
    """Separa P-core ed E-core in base alla frequenza massima dichiarata."""
    mx = cpu_max_freqs()
    if not mx:
        return {"performance": [], "efficiency": [], "all": list(range(os.cpu_count() or 1))}
    top = max(mx.values())
    perf = [c for c, f in mx.items() if f >= top * 0.95]
    eff = [c for c, f in mx.items() if f < top * 0.95]
    return {"performance": sorted(perf), "efficiency": sorted(eff), "all": sorted(mx)}


def physical_performance_cores() -> list[int]:
    """Un solo thread logico per ogni P-core fisico (evita l'SMT)."""
    perf = classify_cores()["performance"]
    seen, out = set(), []
    for c in perf:
        sib = (CPU_DIR / f"cpu{c}" / "topology" / "thread_siblings_list")
        key = sib.read_text().strip() if sib.exists() else str(c)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _read_temp() -> float | None:
    for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        try:
            if (zone / "type").read_text().strip() in ("x86_pkg_temp", "acpitz", "TCPU"):
                return int((zone / "temp").read_text()) / 1000.0
        except Exception:
            continue
    return None


class Sampler:
    """Campiona frequenze per-core e temperatura in background."""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.samples: list[tuple[float, dict[int, float], float | None]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._paths = {int(c.name[3:]): c / "cpufreq" / "scaling_cur_freq"
                       for c in sorted(CPU_DIR.glob("cpu[0-9]*"))
                       if (c / "cpufreq" / "scaling_cur_freq").exists()}

    def _loop(self) -> None:
        t0 = time.perf_counter()
        while not self._stop.is_set():
            freqs = {}
            for cpu, path in self._paths.items():
                try:
                    freqs[cpu] = int(path.read_text()) / 1000.0  # MHz
                except Exception:
                    pass
            self.samples.append((time.perf_counter() - t0, freqs, _read_temp()))
            self._stop.wait(self.interval)

    def __enter__(self) -> "Sampler":
        self._stop.clear()
        self.samples.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def summary(self, skip_first: float = 0.0) -> dict:
        """Frequenze medie per tipo di core e temperatura massima."""
        cores = classify_cores()
        rows = [s for s in self.samples if s[0] >= skip_first]
        if not rows:
            return {}

        def avg(group: list[int]) -> float | None:
            vals = [f for _, freqs, _ in rows for c, f in freqs.items() if c in group]
            return st.fmean(vals) if vals else None

        def busy_avg(group: list[int]) -> float | None:
            """Media limitata ai core effettivamente attivi (frequenza > 1.2 GHz)."""
            vals = [f for _, freqs, _ in rows for c, f in freqs.items() if c in group and f > 1200]
            return st.fmean(vals) if vals else None

        temps = [t for _, _, t in rows if t is not None]
        return {
            "samples": len(rows),
            "freq_p_mean_mhz": avg(cores["performance"]),
            "freq_e_mean_mhz": avg(cores["efficiency"]),
            "freq_p_busy_mhz": busy_avg(cores["performance"]),
            "freq_e_busy_mhz": busy_avg(cores["efficiency"]),
            "freq_max_mhz": max((f for _, fr, _ in rows for f in fr.values()), default=None),
            "temp_mean_c": st.fmean(temps) if temps else None,
            "temp_max_c": max(temps) if temps else None,
        }

    def timeline(self) -> list[tuple[float, float, float | None]]:
        """(t, frequenza media dei core attivi, temperatura) per i grafici."""
        out = []
        for t, freqs, temp in self.samples:
            busy = [f for f in freqs.values() if f > 1200]
            out.append((t, st.fmean(busy) if busy else 0.0, temp))
        return out


if __name__ == "__main__":
    print("core:", classify_cores())
    print("P-core fisici:", physical_performance_cores())
    with Sampler(0.05) as s:
        time.sleep(1.0)
    print(s.summary())
