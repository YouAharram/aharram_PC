from __future__ import annotations

import os

for _var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_var, "1")

import cv2  # noqa: E402

cv2.setNumThreads(0)  # disabilita il thread pool interno di OpenCV

__all__ = ["core", "dataset", "pipelines", "bench", "plots", "sysinfo"]
