from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt      # noqa: E402
import pandas as pd                  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config as C          # noqa: E402

# --- palette ----------------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8983"
GRID = "#e6e5e1"
REF = "#9a9992"                       # riferimento ideale (non e' una serie)

# rampa ordinale blu per i tre livelli di workload
LEVEL_COLOR = {"light": "#86b6ef", "medium": "#2a78d6", "heavy": "#104281"}
LEVEL_MARKER = {"light": "o", "medium": "s", "heavy": "^"}
LEVEL_LABEL = {"light": "light", "medium": "medium", "heavy": "heavy"}
LEVELS = ["light", "medium", "heavy"]

# tinte categoriali (ordine fisso, mai riciclato)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARKERS = ["o", "s", "^", "D", "v"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 10, "axes.titlesize": 11.5, "axes.labelsize": 10,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "legend.frameon": False, "legend.fontsize": 9,
    "lines.linewidth": 2.0, "lines.markersize": 6.5,
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight",
})


def _ax(ax, title: str = "", xlabel: str = "", ylabel: str = "", note: str = "") -> None:
    if title:
        ax.set_title(title, color=INK, pad=10, loc="left", fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    if note:
        ax.annotate(note, xy=(0, -0.19), xycoords="axes fraction", fontsize=8, color=MUTED)


def _save(fig, name: str) -> Path:
    path = C.FIGURES / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  -> {path.name}")
    return path


def _read(name: str) -> pd.DataFrame | None:
    p = C.RESULTS / f"{name}.csv"
    if not p.exists():
        print(f"  (salto {name}: {p.name} assente)")
        return None
    return pd.read_csv(p)


def _worker_axis(ax, workers) -> None:
    ax.set_xscale("log", base=2)
    ax.set_xticks(list(workers))
    ax.set_xticklabels([str(int(w)) for w in workers])
    ax.minorticks_off()


# ===========================================================================
# Strong scaling
# ===========================================================================

def strong_scaling(df: pd.DataFrame) -> None:
    par = df[df.backend == "process"]
    seq = df[df.backend == "sequential"].set_index("level")
    workers = sorted(par.workers.unique())
    n_img = int(par.n_images.iloc[0])

    # --- fig 1: sequenziale vs parallelo -----------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = range(len(LEVELS))
    w = 0.38
    t1 = [seq.loc[lv, "time_median"] for lv in LEVELS]
    best = [par[par.level == lv].time_median.min() for lv in LEVELS]
    bestp = [int(par.loc[par[par.level == lv].time_median.idxmin(), "workers"]) for lv in LEVELS]
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], t1, w, color=MUTED, label="sequenziale (T$_1$)")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], best, w, color=CAT[0],
                label="parallelo (miglior numero di worker)")
    for rect, v in zip(b1, t1):
        ax.annotate(f"{v:.2f}s", (rect.get_x() + rect.get_width() / 2, v), ha="center",
                    va="bottom", fontsize=8.5, color=INK2)
    for rect, v, p, s in zip(b2, best, bestp, [a / b for a, b in zip(t1, best)]):
        ax.annotate(f"{v:.2f}s\np={p} · {s:.1f}x", (rect.get_x() + rect.get_width() / 2, v),
                    ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.set_xticks(list(x))
    ax.set_xticklabels([LEVEL_LABEL[lv] for lv in LEVELS])
    ax.set_ylim(0, max(t1) * 1.28)
    ax.grid(axis="x", visible=False)
    _ax(ax, "Tempo di esecuzione: sequenziale vs parallelo",
        "workload di augmentation", "tempo [s]",
        f"{n_img} immagini 512x512 -> 256x256; mediana su {int(par.reps.iloc[0])} ripetizioni")
    ax.legend(loc="upper left")
    _save(fig, "fig01_sequenziale_vs_parallelo.png")

    # --- fig 2: tempo vs worker --------------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for lv in LEVELS:
        d = par[par.level == lv].sort_values("workers")
        ax.errorbar(d.workers, d.time_median, yerr=d.time_ci95, color=LEVEL_COLOR[lv],
                    marker=LEVEL_MARKER[lv], label=LEVEL_LABEL[lv], capsize=2.5, elinewidth=1)
        ax.annotate(LEVEL_LABEL[lv], (d.workers.iloc[-1], d.time_median.iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=9, color=LEVEL_COLOR[lv])
    ax.set_yscale("log")
    _worker_axis(ax, workers)
    _ax(ax, "Tempo di esecuzione al variare del numero di worker", "numero di worker",
        "tempo [s] (scala log)",
        "barre = intervallo di confidenza al 95%; scheduling dinamico, chunk = 16")
    ax.legend(title="augmentation", loc="lower left")
    _save(fig, "fig02_tempo_vs_worker.png")

    # --- fig 3: speedup + ideale -------------------------------------------
    # Scala doppio-logaritmica: su assi lineari la retta ideale (fino a 40x)
    # schiaccerebbe le curve misurate (~5x) rendendole indistinguibili.
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.plot(workers, workers, color=REF, ls="--", lw=1.6, label="ideale S(p) = p", zorder=1)
    for k, lv in enumerate(LEVELS):
        d = par[par.level == lv].sort_values("workers")
        ax.plot(d.workers, d.speedup, color=LEVEL_COLOR[lv], marker=LEVEL_MARKER[lv],
                label=LEVEL_LABEL[lv], zorder=3)
        i = d.speedup.idxmax()
        ax.annotate(f"{d.loc[i, 'speedup']:.2f}x (p={int(d.loc[i, 'workers'])})",
                    (d.loc[i, "workers"], d.loc[i, "speedup"]),
                    xytext=[(-14, 26), (12, 8), (12, -16)][k], textcoords="offset points",
                    ha=["right", "left", "left"][k], fontsize=8.5, color=LEVEL_COLOR[lv],
                    arrowprops=dict(arrowstyle="-", color=LEVEL_COLOR[lv], lw=0.8,
                                    shrinkA=1, shrinkB=3))
    ax.axvline(C.PHYSICAL_CORES, color=GRID, lw=1.2, zorder=0)
    ax.annotate("14 core fisici", (C.PHYSICAL_CORES, 1.05), xytext=(-4, 0),
                textcoords="offset points", rotation=90, fontsize=8, color=MUTED,
                ha="right", va="bottom")
    _worker_axis(ax, workers)
    ax.set_yscale("log")
    ax.set_yticks([1, 2, 5, 10, 20, 40])
    ax.set_yticklabels(["1x", "2x", "5x", "10x", "20x", "40x"])
    ax.set_ylim(0.8, 48)
    _ax(ax, "Speedup misurato contro speedup ideale", "numero di worker",
        "speedup  S(p) = T$_1$/T$_p$  (scala log)",
        "assi log-log: la retta ideale resta una retta e le curve misurate restano leggibili")
    ax.legend(title="augmentation", loc="upper left")
    _save(fig, "fig03_speedup_vs_ideale.png")

    # zoom senza la retta ideale
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for lv in LEVELS:
        d = par[par.level == lv].sort_values("workers")
        ax.errorbar(d.workers, d.speedup, color=LEVEL_COLOR[lv], marker=LEVEL_MARKER[lv],
                    label=LEVEL_LABEL[lv])
    ax.axhline(1.0, color=REF, ls=":", lw=1.2)
    ax.annotate("nessun guadagno", (workers[0], 1.0), xytext=(2, 4),
                textcoords="offset points", fontsize=8, color=MUTED)
    _worker_axis(ax, workers)
    _ax(ax, "Speedup per workload (dettaglio)", "numero di worker", "speedup",
        "piu' l'augmentation e' costosa, piu' la parallelizzazione rende")
    ax.legend(title="augmentation")
    _save(fig, "fig04_speedup_dettaglio.png")

    # --- fig 5: efficienza --------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for lv in LEVELS:
        d = par[par.level == lv].sort_values("workers")
        ax.plot(d.workers, d.efficiency * 100, color=LEVEL_COLOR[lv],
                marker=LEVEL_MARKER[lv], label=LEVEL_LABEL[lv])
    ax.axhline(100, color=REF, ls="--", lw=1.6)
    ax.annotate("efficienza ideale 100%", (workers[0], 100), xytext=(2, 4),
                textcoords="offset points", fontsize=8, color=MUTED)
    ax.axhline(50, color=GRID, lw=1)
    _worker_axis(ax, workers)
    ax.set_ylim(0, 112)
    _ax(ax, "Efficienza parallela", "numero di worker", "efficienza  E(p) = S(p)/p  [%]",
        "sotto il 50% ogni worker aggiunto restituisce meno di mezzo core di lavoro utile")
    ax.legend(title="augmentation")
    _save(fig, "fig05_efficienza.png")

    # --- fig 6: throughput --------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for lv in LEVELS:
        d = par[par.level == lv].sort_values("workers")
        ax.plot(d.workers, d.throughput_median, color=LEVEL_COLOR[lv],
                marker=LEVEL_MARKER[lv], label=LEVEL_LABEL[lv])
        i = d.throughput_median.idxmax()
        ax.annotate(f"{d.loc[i, 'throughput_median']:.0f} img/s",
                    (d.loc[i, "workers"], d.loc[i, "throughput_median"]), xytext=(6, 4),
                    textcoords="offset points", fontsize=8.5, color=LEVEL_COLOR[lv])
    ax.set_yscale("log")
    _worker_axis(ax, workers)
    _ax(ax, "Throughput", "numero di worker", "immagini elaborate al secondo (scala log)",
        "il picco individua il numero ottimale di worker per ciascun workload")
    ax.legend(title="augmentation")
    _save(fig, "fig06_throughput.png")

    # --- fig 7: wall-clock vs CPU time --------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9), sharex=True)
    for ax, lv in zip(axes, LEVELS):
        d = par[par.level == lv].sort_values("workers")
        t1v = seq.loc[lv, "time_median"]
        ax.plot(d.workers, d.time_median, color=CAT[0], marker=MARKERS[0], label="wall-clock")
        ax.plot(d.workers, d.cpu_total_median, color=CAT[1], marker=MARKERS[1],
                label="CPU time totale (master + worker)")
        ax.axhline(t1v, color=REF, ls="--", lw=1.4)
        ax.annotate("T$_1$", (d.workers.iloc[0], t1v), xytext=(2, 4),
                    textcoords="offset points", fontsize=8, color=MUTED)
        _worker_axis(ax, sorted(d.workers.unique()))
        ax.set_yscale("log")
        _ax(ax, LEVEL_LABEL[lv], "numero di worker", "tempo [s]" if lv == "light" else "")
    axes[0].legend(loc="upper left")
    fig.suptitle("Wall-clock time contro CPU time complessivo", x=0.005, ha="left",
                 fontweight="bold", fontsize=11.5)
    fig.text(0.005, -0.03, "il CPU time cresce con p a parita' di lavoro utile: e' il costo "
                           "in risorse della parallelizzazione", fontsize=8, color=MUTED)
    fig.tight_layout()
    _save(fig, "fig07_wallclock_vs_cpu.png")


# ===========================================================================
def weak_scaling(df: pd.DataFrame) -> None:
    par = df[df.backend == "process"]
    workers = sorted(par.workers.unique())
    per_worker = int(par.per_worker.iloc[0])

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3))
    ax = axes[0]
    for lv in LEVELS:
        d = par[par.level == lv].sort_values("workers")
        if d.empty:
            continue
        ax.errorbar(d.workers, d.time_median, yerr=d.time_ci95, color=LEVEL_COLOR[lv],
                    marker=LEVEL_MARKER[lv], label=LEVEL_LABEL[lv], capsize=2.5, elinewidth=1)
        t0 = df[(df.level == lv) & (df.backend == "sequential")].time_median.iloc[0]
        ax.axhline(t0, color=LEVEL_COLOR[lv], ls=":", lw=1.2, alpha=0.7)
    _worker_axis(ax, workers)
    ax.set_yscale("log")
    _ax(ax, "Tempo di esecuzione (ideale: piatto)", "numero di worker  (N = p x %d immagini)" % per_worker,
        "tempo [s] (scala log)", "le linee punteggiate sono T(1, %d immagini)" % per_worker)
    ax.legend(title="augmentation")

    ax = axes[1]
    for lv in LEVELS:
        d = par[par.level == lv].sort_values("workers")
        if d.empty:
            continue
        ax.plot(d.workers, d.weak_efficiency * 100, color=LEVEL_COLOR[lv],
                marker=LEVEL_MARKER[lv], label=LEVEL_LABEL[lv])
    ax.axhline(100, color=REF, ls="--", lw=1.6)
    ax.annotate("ideale 100%", (workers[0], 100), xytext=(2, 4), textcoords="offset points",
                fontsize=8, color=MUTED)
    _worker_axis(ax, workers)
    ax.set_ylim(0, 115)
    _ax(ax, "Weak efficiency  E$_w$(p) = T(1,n) / T(p,pn)", "numero di worker",
        "efficienza weak [%]", "carico costante per worker: %d immagini" % per_worker)
    ax.legend(title="augmentation")
    fig.tight_layout()
    _save(fig, "fig08_weak_scaling.png")


# ===========================================================================
def chunk_size(df: pd.DataFrame) -> None:
    par = df[df.backend == "process"].copy()
    par["chunksize"] = par.chunksize.astype(float)
    ps = sorted(par.workers.unique())

    fig, axes = plt.subplots(1, len(ps), figsize=(5.7 * len(ps), 4.4), squeeze=False)
    for ax, p in zip(axes[0], ps):
        best = []
        for lv in LEVELS:
            d = par[(par.level == lv) & (par.workers == p)].sort_values("chunksize")
            if d.empty:
                continue
            norm = d.time_median / d.time_median.min()
            ax.plot(d.chunksize, norm, color=LEVEL_COLOR[lv], marker=LEVEL_MARKER[lv],
                    label=LEVEL_LABEL[lv])
            i = d.time_median.idxmin()
            ax.plot([d.loc[i, "chunksize"]], [1.0], marker="o", ms=11, mfc="none",
                    mec=LEVEL_COLOR[lv], mew=1.6, zorder=5)
            best.append(f"{LEVEL_LABEL[lv]}: {int(d.loc[i, 'chunksize'])}")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_yticks([1, 1.5, 2, 3, 4, 6])
        ax.set_yticklabels(["1.0", "1.5", "2.0", "3.0", "4.0", "6.0"])
        ax.minorticks_off()
        ax.axhline(1.0, color=REF, ls="--", lw=1.2)
        ax.annotate("cerchio = chunk ottimo  |  " + ",  ".join(best),
                    xy=(0.02, 0.94), xycoords="axes fraction", fontsize=8.5, color=INK2)
        _ax(ax, f"p = {int(p)} worker", "dimensione del chunk [immagini per task]",
            "tempo normalizzato al minimo (scala log)")
        ax.legend(title="augmentation", loc="upper left", bbox_to_anchor=(0, 0.9))
    fig.tight_layout()
    _save(fig, "fig09_chunk_size.png")


# ===========================================================================
def load_balancing(df: pd.DataFrame) -> None:
    par = df[df.strategy != "sequential"].copy()
    orders = list(par.order.unique())
    strategies = ["static", "dynamic(1)", "dynamic(8)", "dynamic(32)", "dynamic(128)"]
    # dynamic(k) e' una scala ORDINATA per granularita' crescente: rampa a una
    # tinta, non quattro tinte scorrelate. static non appartiene alla famiglia:
    # e' una strategia diversa e prende il neutro.
    colors = {"static": MUTED, "dynamic(1)": "#86b6ef", "dynamic(8)": "#3987e5",
              "dynamic(32)": "#1c5cab", "dynamic(128)": "#0d366b"}
    ps = sorted(par.workers.unique())

    fig, axes = plt.subplots(2, len(orders), figsize=(6.2 * len(orders), 8.4),
                             squeeze=False, sharey="row")
    width = 0.8 / len(strategies)
    for j, order in enumerate(orders):
        for row, (col, title, ylab) in enumerate([
                ("time_median", "Tempo di esecuzione", "tempo [s]"),
                ("imbalance_median", "Sbilanciamento", "max / media del tempo occupato per worker")]):
            ax = axes[row][j]
            for k, st in enumerate(strategies):
                d = par[(par.order == order) & (par.strategy == st)].sort_values("workers")
                if d.empty:
                    continue
                xs = [i + (k - len(strategies) / 2 + 0.5) * width for i in range(len(ps))]
                ax.bar(xs, d[col], width * 0.9, color=colors[st], label=st if row == 0 else None)
            if row == 1:
                ax.axhline(1.0, color=REF, ls="--", lw=1.4)
                if j == 0:
                    ax.set_ylabel("max / media del tempo occupato per worker\n"
                                  "(1.0 = bilanciamento perfetto)")
            ax.set_xticks(range(len(ps)))
            ax.set_xticklabels([f"p={int(v)}" for v in ps])
            ax.grid(axis="x", visible=False)
            if not (row == 1 and j == 0):
                _ax(ax, f"{title} - dataset '{order}'", "", ylab if j == 0 else "")
            else:
                _ax(ax, f"{title} - dataset '{order}'", "", "")
    axes[0][0].legend(ncol=5, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, 1.06))
    fig.suptitle("Assegnamento statico contro assegnamento dinamico su dataset eterogeneo",
                 x=0.005, ha="left", fontweight="bold", fontsize=12.5, y=1.02)
    fig.tight_layout()
    _save(fig, "fig10_load_balancing.png")


# ===========================================================================
def end_to_end(df: pd.DataFrame) -> None:
    par = df[df.backend == "process"]
    seq = df[df.backend == "sequential"]
    workers = sorted(par.workers.unique())
    scopes = [("compute", "solo calcolo (immagini in RAM)"), ("end_to_end", "end-to-end (disco -> disco)")]

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3))
    ax = axes[0]
    for k, (scope, label) in enumerate(scopes):
        d = par[par.pipeline_scope == scope].sort_values("workers")
        ax.plot(d.workers, d.time_median, color=CAT[k], marker=MARKERS[k], label=label)
        t1v = seq[seq.pipeline_scope == scope].time_median.iloc[0]
        ax.axhline(t1v, color=CAT[k], ls=":", lw=1.2, alpha=0.7)
    _worker_axis(ax, workers)
    ax.set_yscale("log")
    _ax(ax, "Tempo di esecuzione", "numero di worker", "tempo [s] (scala log)",
        "le linee punteggiate sono i rispettivi tempi sequenziali T$_1$")
    ax.legend()

    ax = axes[1]
    ax.plot(workers, workers, color=REF, ls="--", lw=1.6, label="ideale")
    for k, (scope, label) in enumerate(scopes):
        d = par[par.pipeline_scope == scope].sort_values("workers")
        ax.plot(d.workers, d.speedup, color=CAT[k], marker=MARKERS[k], label=label)
        i = d.speedup.idxmax()
        ax.annotate(f"{d.loc[i, 'speedup']:.2f}x", (d.loc[i, "workers"], d.loc[i, "speedup"]),
                    xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=CAT[k])
    _worker_axis(ax, workers)
    ax.set_ylim(0, max(workers) * 1.05)
    _ax(ax, "Speedup", "numero di worker", "speedup",
        "decodifica e codifica JPEG scalano bene; il limite e' il costo per immagine piu' alto")
    ax.legend()
    fig.tight_layout()
    _save(fig, "fig11_end_to_end.png")


# ===========================================================================
def overhead(df: pd.DataFrame) -> None:
    # --- creazione del pool -------------------------------------------------
    a = df[df.section == "A_pool_creation"]
    if not a.empty:
        fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3))
        ax = axes[0]
        k = 0
        for ds in a.parent_dataset.unique():
            for m in a[a.parent_dataset == ds].start_method.unique():
                d = a[(a.parent_dataset == ds) & (a.start_method == m)].sort_values("workers")
                rss = d.parent_rss_gb.iloc[0]
                ax.plot(d.workers, d.total_s * 1000, color=CAT[k % len(CAT)],
                        marker=MARKERS[k % len(MARKERS)], label=f"{m}, padre {rss:.2f} GB")
                k += 1
        _worker_axis(ax, sorted(a.workers.unique()))
        ax.set_yscale("log")
        _ax(ax, "Costo di creazione e distruzione del pool", "numero di worker",
            "tempo [ms] (scala log)",
            "con fork il costo cresce con la memoria del processo padre (copia delle page table)")
        ax.legend(fontsize=8.5)

        ax = axes[1]
        k = 0
        for ds in a.parent_dataset.unique():
            for m in a[a.parent_dataset == ds].start_method.unique():
                d = a[(a.parent_dataset == ds) & (a.start_method == m)].sort_values("workers")
                ax.plot(d.workers, d.per_worker_ms, color=CAT[k % len(CAT)],
                        marker=MARKERS[k % len(MARKERS)],
                        label=f"{m}, padre {d.parent_rss_gb.iloc[0]:.2f} GB")
                k += 1
        _worker_axis(ax, sorted(a.workers.unique()))
        _ax(ax, "Costo per singolo worker", "numero di worker", "tempo [ms per worker]",
            "spawn deve reimportare l'interprete e le librerie in ogni processo")
        ax.legend(fontsize=8.5)
        fig.tight_layout()
        _save(fig, "fig12_overhead_creazione_pool.png")

    # --- IPC ----------------------------------------------------------------
    b = df[df.section == "B_ipc"]
    if not b.empty:
        levels = [lv for lv in LEVELS if lv in set(b.level)]
        fig, axes = plt.subplots(1, len(levels), figsize=(5.7 * len(levels), 4.3), squeeze=False)
        for ax, lv in zip(axes[0], levels):
            for k, mode in enumerate(["reduce", "array"]):
                d = b[(b.level == lv) & (b.return_mode == mode) & (b.backend == "process")]
                d = d.sort_values("workers")
                label = "riduzione scalare (8 B/immagine)" if mode == "reduce" \
                    else "immagine completa (196 KB/immagine)"
                ax.plot(d.workers, d.speedup, color=CAT[k], marker=MARKERS[k], label=label)
            ws = sorted(b.workers.unique())
            ax.plot(ws, ws, color=REF, ls="--", lw=1.4, label="ideale")
            _worker_axis(ax, ws)
            _ax(ax, f"workload {lv}", "numero di worker", "speedup",
                "restituire le immagini al master introduce serializzazione e copia")
            ax.legend(fontsize=8.5)
        fig.suptitle("Costo di comunicazione dei risultati (IPC)", x=0.005, ha="left",
                     fontweight="bold", fontsize=12)
        fig.tight_layout()
        _save(fig, "fig13_overhead_ipc.png")

    # --- pool persistente ---------------------------------------------------
    c = df[df.section == "C_persistent"]
    if not c.empty:
        fig, ax = plt.subplots(figsize=(7.6, 4.3))
        ps = sorted(c[c.pool == "fresh"].workers.unique())
        width = 0.35
        for k, kind in enumerate(["fresh", "persistent"]):
            label = "pool ricreato a ogni batch" if kind == "fresh" else "pool persistente riutilizzato"
            xs, ys = [], []
            for i, lv in enumerate(LEVELS):
                for j, p in enumerate(ps):
                    d = c[(c.level == lv) & (c.pool == kind) & (c.workers == p)]
                    if d.empty:
                        continue
                    xs.append(i * (len(ps) + 0.6) + j + (k - 0.5) * width)
                    ys.append(d.speedup.iloc[0])
            ax.bar(xs, ys, width * 0.92, color=CAT[k], label=label)
        ticks, labels = [], []
        for i, lv in enumerate(LEVELS):
            for j, p in enumerate(ps):
                ticks.append(i * (len(ps) + 0.6) + j)
                labels.append(f"{int(p)}")
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels)
        for i, lv in enumerate(LEVELS):
            ax.annotate(LEVEL_LABEL[lv], (i * (len(ps) + 0.6) + (len(ps) - 1) / 2, -0.14),
                        xycoords=("data", "axes fraction"), ha="center", fontsize=9.5, color=INK)
        ax.grid(axis="x", visible=False)
        _ax(ax, "Speedup con pool ricreato contro pool persistente", "numero di worker", "speedup",
            "\n\nriutilizzare i processi elimina il costo di fork: conta soprattutto per i workload leggeri")
        ax.legend()
        fig.tight_layout()
        _save(fig, "fig14_pool_persistente.png")

    # --- thread vs processi -------------------------------------------------
    d0 = df[df.section == "D_backend"]
    if not d0.empty:
        levels = [lv for lv in LEVELS if lv in set(d0.level)]
        fig, axes = plt.subplots(1, len(levels), figsize=(5.4 * len(levels), 4.3), squeeze=False)
        for ax, lv in zip(axes[0], levels):
            for k, backend in enumerate(["process", "thread"]):
                d = d0[(d0.level == lv) & (d0.backend == backend)].sort_values("workers")
                ax.plot(d.workers, d.speedup, color=CAT[k], marker=MARKERS[k],
                        label="processi" if backend == "process" else "thread")
            ws = sorted(d0.workers.unique())
            ax.plot(ws, ws, color=REF, ls="--", lw=1.4, label="ideale")
            _worker_axis(ax, ws)
            _ax(ax, f"workload {lv}", "numero di worker", "speedup")
            ax.legend(fontsize=8.5)
        fig.suptitle("Thread contro processi: quanto pesa il GIL", x=0.005, ha="left",
                     fontweight="bold", fontsize=12)
        fig.text(0.005, -0.03, "OpenCV rilascia il GIL nelle chiamate native, quindi i thread "
                               "guadagnano qualcosa; il codice Python di Albumentations no",
                 fontsize=8, color=MUTED)
        fig.tight_layout()
        _save(fig, "fig15_thread_vs_processi.png")

    # --- parallelismo intra-immagine ---------------------------------------
    e = df[df.section == "E_intra_image"]
    if not e.empty:
        fig, ax = plt.subplots(figsize=(7.2, 4.3))
        for k, lv in enumerate([lv for lv in LEVELS if lv in set(e.level)]):
            d = e[e.level == lv].sort_values("cv2_threads")
            ax.plot(d.cv2_threads, d.speedup, color=LEVEL_COLOR[lv], marker=LEVEL_MARKER[lv],
                    label=f"{lv}: thread interni di OpenCV")
        ws = sorted(e.cv2_threads.unique())
        ax.plot(ws, ws, color=REF, ls="--", lw=1.4, label="ideale")
        ax.set_xscale("log", base=2)
        ax.set_xticks(ws)
        ax.set_xticklabels([str(int(w)) for w in ws])
        ax.minorticks_off()
        _ax(ax, "Parallelismo intra-immagine (thread interni di OpenCV)",
            "thread OpenCV su una singola immagine", "speedup",
            "parallelizzare dentro l'immagine rende molto meno che parallelizzare fra immagini")
        ax.legend(fontsize=8.5)
        _save(fig, "fig16_parallelismo_intra_immagine.png")


# ===========================================================================
def saturation(df: pd.DataFrame, timeline_json: Path | None = None) -> None:
    b = df[df.section == "B_frequency"]
    if not b.empty:
        fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3))
        ax = axes[0]
        d = b.sort_values("workers")
        ax.plot(d.workers, d.freq_p_busy_mhz, color=CAT[0], marker=MARKERS[0],
                label="P-core attivi")
        ax.plot(d.workers, d.freq_e_busy_mhz, color=CAT[1], marker=MARKERS[1],
                label="E-core attivi")
        _worker_axis(ax, sorted(d.workers.unique()))
        _ax(ax, "Frequenza di clock in funzione del carico", "numero di worker",
            "frequenza media dei core attivi [MHz]",
            "T$_1$ e' misurato in turbo su un solo core: parte dello speedup mancante e' fisica")
        ax.legend()

        ax = axes[1]
        ax.plot(d.workers, d.speedup, color=CAT[0], marker=MARKERS[0], label="speedup misurato")
        ratio = d.freq_p_busy_mhz / d.freq_p_busy_mhz.iloc[0]
        ax.plot(d.workers, d.workers * ratio, color=CAT[2], marker=MARKERS[2],
                label="ideale corretto per la frequenza")
        ax.plot(d.workers, d.workers, color=REF, ls="--", lw=1.4, label="ideale S(p) = p")
        _worker_axis(ax, sorted(d.workers.unique()))
        _ax(ax, "Speedup contro tetto realistico", "numero di worker", "speedup",
            "il tetto corretto tiene conto del calo di frequenza, non ancora degli E-core")
        ax.legend()
        fig.tight_layout()
        _save(fig, "fig17_frequenza_e_speedup.png")

    c = df[df.section == "C_affinity"]
    if not c.empty:
        fig, ax = plt.subplots(figsize=(8.2, 4.3))
        d = c.copy()
        colors = [MUTED if "1 P-core" in a else CAT[0] if "P-core" in a
                  else CAT[1] if "E-core" in a else CAT[2] for a in d.affinity]
        bars = ax.bar(range(len(d)), d.throughput_median, 0.62, color=colors)
        for rect, v, s in zip(bars, d.throughput_median, d.speedup):
            ax.annotate(f"{v:.0f} img/s\n{s:.2f}x", (rect.get_x() + rect.get_width() / 2, v),
                        ha="center", va="bottom", fontsize=8.5, color=INK2)
        ax.set_xticks(range(len(d)))
        ax.set_xticklabels([f"{a}\n({int(w)} worker)" for a, w in zip(d.affinity, d.workers)],
                           fontsize=8.5)
        ax.set_ylim(0, d.throughput_median.max() * 1.22)
        ax.grid(axis="x", visible=False)
        _ax(ax, "Throughput per tipo di core (affinita' forzata)", "",
            "immagini al secondo",
            "misurato con os.sched_setaffinity sul processo padre, ereditata dai worker")
        _save(fig, "fig18_affinita_core.png")

    if timeline_json and timeline_json.exists():
        import json
        data = json.loads(timeline_json.read_text())
        tl = data["timeline"]
        fig, axes = plt.subplots(2, 1, figsize=(8.4, 5.6), sharex=True)
        ts = [r["t"] for r in tl]
        axes[0].plot(ts, [r["freq_mhz"] for r in tl], color=CAT[0], lw=1.6)
        _ax(axes[0], f"Carico sostenuto a {data['workers']} worker: frequenza", "",
            "frequenza media dei core attivi [MHz]")
        f0, f1 = data.get("freq_start_mhz", 0), data.get("freq_end_mhz", 0)
        axes[0].axhline(f0, color=REF, ls="--", lw=1.3)
        axes[0].annotate(f"media primi 15%: {f0:.0f} MHz    media ultimi 15%: {f1:.0f} MHz"
                         f"    ({f1 / f0 - 1:+.1%})", xy=(0.02, 0.94),
                         xycoords="axes fraction", fontsize=8.5, color=INK2)
        temps = [r["temp_c"] for r in tl if r["temp_c"] is not None]
        if temps:
            axes[1].plot(ts[:len(temps)], temps, color=CAT[1], lw=1.6)
        _ax(axes[1], "Temperatura del package", "tempo dall'inizio della corsa [s]",
            "temperatura [C]")
        fig.text(0.005, -0.035,
                 "nessun transitorio: la macchina e' gia' al limite termico dal primo istante, "
                 "quindi il throttling e' lo stato stazionario, non un degrado progressivo",
                 fontsize=8, color=MUTED)
        fig.tight_layout()
        _save(fig, "fig19_throttling_termico.png")


# ===========================================================================
def cache_behavior(df: pd.DataFrame, l3_mb: float = 24.0) -> None:
    seq = df[df.backend == "sequential"].sort_values("image_size")
    par = df[df.backend == "process"]
    ps = sorted(par.workers.unique())

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.4))
    ax = axes[0]
    ax.plot(seq.image_size, seq.ns_per_pixel, color=MUTED, marker="o", label="sequenziale")
    for k, p_ in enumerate(ps):
        d = par[par.workers == p_].sort_values("image_size")
        ax.plot(d.image_size, d.ns_per_pixel, color=CAT[k], marker=MARKERS[k],
                label=f"{int(p_)} worker")
    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted(seq.image_size.unique()))
    ax.set_xticklabels([str(int(v)) for v in sorted(seq.image_size.unique())])
    ax.minorticks_off()
    ax.set_yscale("log")
    _ax(ax, "Costo per pixel a lavoro totale costante", "lato dell'immagine [px]",
        "nanosecondi per pixel (scala log)",
        "il numero totale di pixel elaborati e' lo stesso in ogni punto: cambia solo il working set")
    ax.legend()

    ax = axes[1]
    for k, p_ in enumerate(ps):
        d = par[par.workers == p_].sort_values("aggregate_working_set_mb")
        ax.plot(d.aggregate_working_set_mb, d.efficiency * 100, color=CAT[k],
                marker=MARKERS[k], label=f"{int(p_)} worker")
        for _, r in d.iterrows():
            ax.annotate(f"{int(r.image_size)}px", (r.aggregate_working_set_mb, r.efficiency * 100),
                        xytext=(0, 7), textcoords="offset points", fontsize=7.5,
                        color=CAT[k], ha="center")
    ax.axvline(l3_mb, color=REF, ls="--", lw=1.5)
    ax.annotate(f"L3 = {l3_mb:.0f} MB", (l3_mb, ax.get_ylim()[1]), xytext=(4, -12),
                textcoords="offset points", fontsize=8.5, color=MUTED, va="top")
    ax.set_xscale("log", base=2)
    _ax(ax, "Efficienza parallela contro working set aggregato",
        "working set dei worker attivi [MB, scala log]", "efficienza parallela [%]",
        "oltre la capacita' della L3 condivisa i worker si contendono la memoria")
    ax.legend()
    fig.tight_layout()
    _save(fig, "fig20_cache_working_set.png")


# ===========================================================================
def main() -> None:
    print("Genero le figure in", C.FIGURES)
    failed = []
    jobs = [("02_strong_scaling", strong_scaling), ("03_weak_scaling", weak_scaling),
            ("04_chunk_size", chunk_size), ("05_load_balancing", load_balancing),
            ("06_end_to_end", end_to_end), ("07_overhead", overhead),
            ("09_cache_behavior", cache_behavior)]
    for name, fn in jobs:
        df = _read(name)
        if df is None:
            continue
        try:
            fn(df)
        except Exception as exc:                      # una figura rotta non deve
            failed.append((name, exc))                # fermare tutte le altre
            print(f"  !! figura da {name} non generata: {type(exc).__name__}: {exc}")
    df = _read("08_saturation")
    if df is not None:
        try:
            saturation(df, C.RESULTS / "08_thermal_timeline.json")
        except Exception as exc:
            failed.append(("08_saturation", exc))
            print(f"  !! figura da 08_saturation non generata: {type(exc).__name__}: {exc}")
    if failed:
        print(f"\nATTENZIONE: {len(failed)} gruppi di figure non generati: "
              + ", ".join(n for n, _ in failed))
    else:
        print("Fatto: tutte le figure generate.")


if __name__ == "__main__":
    main()
