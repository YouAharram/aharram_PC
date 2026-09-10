from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def _lscpu() -> dict[str, str]:
    out = _run(["lscpu"])
    info = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return info


def collect() -> dict:
    cpu = _lscpu()
    info: dict = {
        "cpu_model": cpu.get("Model name", platform.processor()),
        "architecture": platform.machine(),
        "logical_cores": os.cpu_count(),
        "physical_cores": None,
        "threads_per_core": cpu.get("Thread(s) per core"),
        "sockets": cpu.get("Socket(s)"),
        "cpu_max_mhz": cpu.get("CPU max MHz"),
        "l1d_cache": cpu.get("L1d cache"),
        "l1i_cache": cpu.get("L1i cache"),
        "l2_cache": cpu.get("L2 cache"),
        "l3_cache": cpu.get("L3 cache"),
        "numa_nodes": cpu.get("NUMA node(s)"),
        "os": f"{platform.system()} {platform.release()}",
        "os_full": platform.version(),
        "kernel": _run(["uname", "-r"]),
        "python": sys.version.split()[0],
        "python_impl": platform.python_implementation(),
    }

    try:
        cores = int(cpu.get("Core(s) per socket", "0")) * int(cpu.get("Socket(s)", "1"))
        info["physical_cores"] = cores or None
    except ValueError:
        pass

    try:
        import psutil

        info["physical_cores"] = psutil.cpu_count(logical=False) or info["physical_cores"]
        vm = psutil.virtual_memory()
        info["ram_total_gb"] = round(vm.total / 1024**3, 2)
        info["ram_available_gb"] = round(vm.available / 1024**3, 2)
    except Exception:
        pass

    versions = {}
    for mod in ("numpy", "cv2", "albumentations", "scipy", "matplotlib", "pandas", "torch"):
        try:
            m = __import__(mod)
            versions[mod] = getattr(m, "__version__", "?")
        except Exception:
            versions[mod] = None
    info["library_versions"] = versions

    try:
        import numpy as np

        cfg = np.show_config(mode="dicts")
        info["numpy_blas"] = cfg.get("Build Dependencies", {}).get("blas", {}).get("name")
        info["numpy_simd"] = cfg.get("SIMD Extensions", {}).get("found")
        info["compiler"] = cfg.get("Compilers", {}).get("c", {}).get("version")
    except Exception:
        pass

    try:
        import cv2

        info["opencv_threads_default"] = cv2.getNumThreads()
        build = cv2.getBuildInformation()
        for line in build.splitlines():
            if "Parallel framework" in line:
                info["opencv_parallel_framework"] = line.split(":", 1)[1].strip()
    except Exception:
        pass

    info["env_thread_limits"] = {
        k: os.environ.get(k)
        for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    }
    load1, load5, load15 = os.getloadavg()
    info["loadavg_at_collection"] = {"1min": load1, "5min": load5, "15min": load15}
    return info


def save(path: str | Path) -> dict:
    info = collect()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(info, indent=2))
    return info


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2))
