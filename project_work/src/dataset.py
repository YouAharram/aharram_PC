"""Generazione e caricamento del dataset di immagini (requisito 1).

Il dataset e' sintetico ma *procedurale e deterministico*: ogni immagine e'
prodotta da un seed derivato dal suo indice, quindi il dataset e' esattamente
riproducibile su qualsiasi macchina senza dover scaricare gigabyte di dati e
senza che le performance dipendano dalla rete o dalla cache del filesystem.

Le immagini contengono gradienti, forme geometriche, texture a bassa frequenza e
grana: strutture con statistiche piu' simili a foto reali rispetto al rumore
puro (importante per trasformazioni come CLAHE, Sharpen o la compressione JPEG).

Parametri facilmente variabili: numero di immagini, dimensione, eterogeneita'
delle dimensioni (usata per gli esperimenti di load balancing).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import numpy as np

cv2.setNumThreads(0)  # nessun parallelismo interno di OpenCV durante la generazione


def make_image(index: int, size: int, *, base_seed: int = 20250908) -> np.ndarray:
    """Immagine RGB uint8 (size x size x 3) deterministica per l'indice dato."""
    rng = np.random.default_rng(base_seed + index)
    h = w = size

    # 1) sfondo: gradiente lineare tra due colori casuali
    c0 = rng.integers(0, 256, 3).astype(np.float32)
    c1 = rng.integers(0, 256, 3).astype(np.float32)
    ramp = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None]
    vert = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    mix = 0.5 * (ramp + vert)
    img = c0[None, None, :] * (1.0 - mix) + c1[None, None, :] * mix

    # 2) texture a bassa frequenza (rumore 16x16 ingrandito = "nuvole")
    low = rng.random((16, 16, 3), dtype=np.float32)
    clouds = cv2.resize(low, (w, h), interpolation=cv2.INTER_CUBIC)
    img = img * (0.75 + 0.5 * clouds)

    img = np.clip(img, 0, 255).astype(np.uint8)

    # 3) forme geometriche (contorni netti -> contenuto ad alta frequenza)
    n_shapes = int(rng.integers(6, 14))
    for _ in range(n_shapes):
        color = tuple(int(v) for v in rng.integers(0, 256, 3))
        kind = rng.integers(0, 3)
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        r = int(rng.integers(size // 20, size // 5))
        if kind == 0:
            cv2.circle(img, (x, y), r, color, -1, lineType=cv2.LINE_AA)
        elif kind == 1:
            cv2.rectangle(img, (x, y), (min(x + r, w), min(y + r, h)), color, -1)
        else:
            x2, y2 = int(rng.integers(0, w)), int(rng.integers(0, h))
            cv2.line(img, (x, y), (x2, y2), color, thickness=int(rng.integers(2, 8)), lineType=cv2.LINE_AA)

    # 4) grana fotografica
    grain = rng.normal(0.0, 6.0, (h, w, 3)).astype(np.float32)
    img = np.clip(img.astype(np.float32) + grain, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(img)


def make_memory_dataset(n_images: int, size: int, *, base_seed: int = 20250908) -> list[np.ndarray]:
    """Dataset in RAM: usato dal *computation benchmark* (nessun I/O nel timing)."""
    return [make_image(i, size, base_seed=base_seed) for i in range(n_images)]


def make_heterogeneous_dataset(
    n_images: int,
    sizes: tuple[int, ...] = (192, 320, 512, 832),
    weights: tuple[float, ...] = (0.55, 0.25, 0.15, 0.05),
    *,
    base_seed: int = 20250908,
    shuffle_seed: int | None = None,
) -> list[np.ndarray]:
    """Dataset con immagini di dimensioni molto diverse.

    Il costo di augmentation cresce ~quadraticamente con il lato, quindi le
    immagini piu' grandi costano ~19x le piu' piccole: e' il caso in cui la
    strategia di load balancing conta davvero (requisito 12).

    Con shuffle_seed=None le immagini sono ordinate per dimensione crescente
    (caso avverso per l'assegnamento statico a blocchi contigui).
    """
    rng = np.random.default_rng(base_seed)
    chosen = rng.choice(len(sizes), size=n_images, p=np.asarray(weights) / np.sum(weights))
    chosen = np.sort(chosen)
    if shuffle_seed is not None:
        np.random.default_rng(shuffle_seed).shuffle(chosen)
    return [make_image(i, int(sizes[c]), base_seed=base_seed) for i, c in enumerate(chosen)]


def load_or_make(n_images: int, size: int, *, cache_dir: str | Path = "data/cache",
                 base_seed: int = 20250908, verbose: bool = True) -> list[np.ndarray]:
    """Dataset uniforme in RAM, con cache su disco per non rigenerarlo ogni volta.

    La generazione (~17 ms/immagine) avviene una sola volta; le esecuzioni
    successive rileggono un unico array .npy. La cache e' fuori dal timing.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"uniform_n{n_images}_s{size}_seed{base_seed}.npy"
    if cache.exists():
        arr = np.load(cache)
        if verbose:
            print(f"  dataset da cache: {cache.name} ({arr.nbytes / 1024**3:.2f} GB)")
        return [np.ascontiguousarray(arr[i]) for i in range(len(arr))]
    if verbose:
        print(f"  genero {n_images} immagini {size}x{size} ...", flush=True)
    imgs = make_memory_dataset(n_images, size, base_seed=base_seed)
    np.save(cache, np.stack(imgs))
    if verbose:
        print(f"  cache scritta in {cache}")
    return imgs


def make_disk_dataset(directory: str | Path, n_images: int, size: int, *, quality: int = 92,
                      base_seed: int = 20250908, force: bool = False) -> list[Path]:
    """Scrive il dataset su disco come JPEG: usato dal benchmark *end-to-end*."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / f"img_{i:06d}.jpg" for i in range(n_images)]
    for i, p in enumerate(paths):
        if force or not p.exists():
            img = make_image(i, size, base_seed=base_seed)
            cv2.imwrite(str(p), cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])
    return paths


def make_targets(index: int, size: int, n_boxes: int = 3, n_kps: int = 5,
                 *, base_seed: int = 20250908) -> dict:
    """Bounding box + keypoint deterministici associati all'immagine `index`."""
    rng = np.random.default_rng(base_seed + 100_000 + index)
    boxes, labels = [], []
    for _ in range(n_boxes):
        x1, y1 = rng.integers(0, size // 2, 2)
        x2 = int(rng.integers(x1 + size // 8, size))
        y2 = int(rng.integers(y1 + size // 8, size))
        boxes.append([float(x1), float(y1), float(min(x2, size - 1)), float(min(y2, size - 1))])
        labels.append(int(rng.integers(0, 5)))
    kps = [(float(rng.integers(0, size)), float(rng.integers(0, size))) for _ in range(n_kps)]
    return {"bboxes": boxes, "labels": labels, "keypoints": kps}


def digest(array: np.ndarray) -> str:
    """SHA-256 dei byte dell'array: identita' esatta dell'output augmentato."""
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def dataset_bytes(images: list[np.ndarray]) -> int:
    return sum(im.nbytes for im in images)


if __name__ == "__main__":
    import time

    t0 = time.perf_counter()
    ds = make_memory_dataset(20, 512)
    dt = time.perf_counter() - t0
    print(f"20 immagini 512x512 generate in {dt:.2f}s ({dt / 20 * 1000:.1f} ms/img)")
    print("shape", ds[0].shape, "dtype", ds[0].dtype, "MB totali", dataset_bytes(ds) / 1024**2)
    print("determinismo:", digest(ds[3]) == digest(make_image(3, 512)))
