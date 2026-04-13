import sys
import os
import multiprocessing
import matplotlib.pyplot as plt
from passlib.hash import des_crypt
from warmup import warmup_system 


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords as run_shared_nothing
from crack_passwords_global import crack_passwords_global_exit as run_global_exit

def plot_gantt(ax, profiling_log, title, color):
    t_zero = min(task[1] for task in profiling_log)
    unique_pids = list(set(task[0] for task in profiling_log))
    pid_to_y = {pid: idx for idx, pid in enumerate(unique_pids)}
    
    for pid, t_start, t_end in profiling_log:
        y_pos = pid_to_y[pid]
        start_rel = t_start - t_zero
        duration = t_end - t_start
        ax.barh(y_pos, width=duration, left=start_rel, color=color, edgecolor='black', height=0.5)

    ax.set_yticks(range(len(unique_pids)))
    ax.set_yticklabels([f"Core {i+1}" for i in range(len(unique_pids))])
    ax.set_xlabel("Tempo di Esecuzione (Secondi)")
    ax.set_title(title)
    ax.grid(True, axis='x', linestyle='--', alpha=0.7)

def main():
    passwords = ["18150615", "18231122", "18300704"]


    salt = "HX"
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in passwords]
    
    start_y = 1800
    end_y = 2020
    test_cores = min(4, multiprocessing.cpu_count())
    warmup_system(target_hashes, salt)

    print("\nEstrazione dei dati di profilazione in corso...")

    print("Raccolta dati: Shared-Nothing...")
    # CHIAMATA AGGIORNATA: Aggiunto return_profile=True
    _, att_local, t_local, log_local = run_shared_nothing(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=test_cores, scheduling="dynamic", return_profile=True
    )

    print("Raccolta dati: Global Early Exit (IPC)...")
    # CHIAMATA AGGIORNATA: Aggiunto return_profile=True
    _, att_global, t_global, log_global = run_global_exit(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=test_cores, return_profile=True
    )

    print("\nGenerazione del grafico Gantt comparativo...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    max_time = max(t_local, t_global) * 1.05
    ax1.set_xlim(0, max_time)
    ax2.set_xlim(0, max_time)
    
    plot_gantt(ax1, log_local, f"Shared-Nothing (Nessun IPC) | Hash: {att_local:,} | Tempo: {t_local:.2f}s", 'dodgerblue')
    plot_gantt(ax2, log_global, f"Global Exit (Manager.dict IPC) | Hash: {att_global:,} | Tempo: {t_global:.2f}s", 'crimson')
    
    plt.tight_layout()
    plot_filename = "results/ipc_paradox_gantt.png"
    plt.savefig(plot_filename, dpi=300)
    print(f"Grafico salvato: {plot_filename}")

if __name__ == "__main__":
    main()
