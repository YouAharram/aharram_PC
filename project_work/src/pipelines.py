"""Pipeline di augmentation Albumentations a tre livelli di costo computazionale.

Requisito 2 del progetto: light / medium / heavy. Le pipeline sono costruite da
una factory in modo che ogni processo worker possa ricrearne una copia locale
(gli oggetti Compose non vengono condivisi tra processi).

Tutte le trasformazioni sono applicate con p=1.0 dove la variabilita' del costo
non e' voluta: cosi' il costo per immagine e' stabile e i tempi misurati non
dipendono dall'estrazione casuale delle trasformazioni. La casualita' resta
comunque presente nei *parametri* di ogni trasformazione (angoli, fattori di
luminosita', ...), cioe' l'augmentation e' realmente randomica.
"""
from __future__ import annotations

import albumentations as A

#: dimensione dell'output di tutte le pipeline (tipica di una CNN di CV)
OUT_SIZE = 256

LEVELS = ("light", "medium", "heavy")


def _light() -> list:
    return [
        A.Resize(OUT_SIZE, OUT_SIZE, interpolation=1),
        A.HorizontalFlip(p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=1.0),
    ]


def _medium() -> list:
    return [
        A.Resize(OUT_SIZE, OUT_SIZE, interpolation=1),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.2),
        A.Rotate(limit=30, p=1.0),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=1.0),
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=1.0),
        A.RGBShift(p=0.5),
    ]


def _heavy() -> list:
    return [
        A.Resize(OUT_SIZE, OUT_SIZE, interpolation=1),
        A.HorizontalFlip(p=0.5),
        A.Affine(scale=(0.8, 1.2), translate_percent=(-0.1, 0.1), rotate=(-30, 30), shear=(-10, 10), p=1.0),
        A.ElasticTransform(alpha=30, sigma=6, p=1.0),
        A.GaussianBlur(blur_limit=(3, 7), p=1.0),
        A.GaussNoise(std_range=(0.05, 0.15), p=1.0),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=1.0),
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=1.0),
        A.CLAHE(clip_limit=4.0, p=1.0),
        A.Sharpen(p=1.0),
    ]


_FACTORIES = {"light": _light, "medium": _medium, "heavy": _heavy}


def build(level: str, *, seed: int | None = None, with_targets: bool = False,
          resize_last: bool = False) -> A.Compose:
    """Crea la pipeline richiesta.

    with_targets=True aggiunge bounding box e keypoint alla pipeline, usati dal
    test di correttezza (requisito 5) per verificare che anche le annotazioni
    restino coerenti dopo le trasformazioni geometriche.

    resize_last=True sposta il Resize in fondo: le trasformazioni lavorano alla
    risoluzione nativa dell'immagine e quindi il costo per immagine diventa
    proporzionale alla sua area. E' la variante usata nell'esperimento di load
    balancing (requisito 12), dove servono task con costi molto diversi.
    """
    if level not in _FACTORIES:
        raise ValueError(f"livello sconosciuto: {level!r} (attesi {LEVELS})")
    transforms = _FACTORIES[level]()
    if resize_last:
        resize = transforms.pop(0)
        transforms.append(resize)
    kwargs: dict = {"seed": seed}
    if with_targets:
        kwargs["bbox_params"] = A.BboxParams(format="pascal_voc", label_fields=["labels"], min_visibility=0.0)
        kwargs["keypoint_params"] = A.KeypointParams(format="xy", remove_invisible=False)
    return A.Compose(transforms, **kwargs)


def describe(level: str) -> list[str]:
    return [t.__class__.__name__ for t in _FACTORIES[level]()]


if __name__ == "__main__":
    for lv in LEVELS:
        print(f"{lv:7s} ({len(describe(lv))} transforms): {', '.join(describe(lv))}")
