import sys
import os
import multiprocessing
import matplotlib.pyplot as plt
from passlib.hash import des_crypt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords
from warmup import warmup_system

def plot_gantt(ax, profiling_log, title, color='dodgerblue'):
    if not profiling_log:
        return
        
    t_zero = min(task[1] for task in profiling_log)
    unique_pids = list(set(task[0] for task in profiling_log))
    
    unique_pids.sort()
    pid_to_y = {pid: idx for idx, pid in enumerate(unique_pids)}
    
    for pid, t_start, t_end in profiling_log:
        y_pos = pid_to_y[pid]
        start_rel = t_start - t_zero
        duration = t_end - t_start
        ax.barh(y_pos, width=duration, left=start_rel, color=color, edgecolor='black', height=0.6)

    ax.set_yticks(range(len(unique_pids)))
    ax.set_yticklabels([f"Core {i+1}" for i in range(len(unique_pids))])
    ax.set_xlabel("Tempo (Secondi)")
    ax.set_title(title)
    ax.grid(True, axis='x', linestyle='--', alpha=0.7)

def main():
    dummy_passwords = ["10000101", "10000202", "10000303"]
    salt = "HX"
    print("Generazione hash target fantasma in corso...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in dummy_passwords]
    
    start_y = 1000
    end_y = 2020
    total_years = end_y - start_y + 1
    
    test_cores = min(4, multiprocessing.cpu_count())
    static_chunk = total_years // test_cores
    warmup_system(target_hashes, salt)

    print("\n" + "="*70)
    print(" PROFILAZIONE LOAD IMBALANCE (FORZATURA CHUNK)")
    print("="*70)
    print(f"Spazio di ricerca:  {total_years} anni totali")
    print(f"Blocco Statico:     {static_chunk} anni/task")
    print(f"Blocco Dinamico:    1 anno/task")

    print("\nEsecuzione in modalità STATIC (Blocchi giganti)...")
    _, _, t_static, log_static = crack_passwords(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y, 
        cores=test_cores, custom_chunksize=static_chunk, return_profile=True
    )

    print("Esecuzione in modalità DYNAMIC (Blocco unitario)...")
    _, _, t_dynamic, log_dynamic = crack_passwords(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y, 
        cores=test_cores, custom_chunksize=1, return_profile=True
    )

    print("\nGenerazione del grafico in corso...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    max_time = max(t_static, t_dynamic) * 1.05
    ax1.set_xlim(0, max_time)
    ax2.set_xlim(0, max_time)
    
    plot_gantt(ax1, log_static, f"Statico (Blocchi da {static_chunk}) | Tempo Totale: {t_static:.2f}s", color='crimson')
    plot_gantt(ax2, log_dynamic, f"Dinamico (Blocchi da 1) | Tempo Totale: {t_dynamic:.2f}s", color='dodgerblue')
    
    plt.tight_layout()
    os.makedirs("results", exist_ok=True)
    plot_filename = "results/load_imbalance_gantt_stress.png"
    plt.savefig(plot_filename, dpi=300)
    print(f"Grafico Gantt salvato in: {plot_filename}")

if __name__ == "__main__":
    main()
