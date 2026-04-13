import sys
import os
import multiprocessing
import csv
from passlib.hash import des_crypt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))

from crack_passwords_sequential import crack_passwords_sequential
from crack_passwords_parallel import crack_passwords as run_shared_nothing
from crack_passwords_global import crack_passwords_global_exit as run_global_exit
from warmup import warmup_system

def main():
    dummy_passwords = ["10000101", "10000202", "10000303"]
    salt = "HX"
    print("Generazione degli hash target in corso...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in dummy_passwords]
    start_y = 1500
    end_y = 2020
    max_cores = multiprocessing.cpu_count()
    core_configs = [1, 2, 4, 8, 16, 20]
    csv_filename = "results/throughput_comparison_data.csv"
    os.makedirs("results", exist_ok=True)
    warmup_system(target_hashes, salt)
   
    print("\n" + "="*75)
    print(" TEST DI THROUGHPUT (CONFRONTO ARCHITETTURALE + SEQUENZIALE)")
    print("="*75)
    print("Calcolo della Baseline Assoluta (Sequenziale Puro)...")
    _, att_seq, t_seq = crack_passwords_sequential(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y
    )
    
    t_seq = max(t_seq, 0.0001) 
    throughput_seq = att_seq / t_seq
    print(f"Throughput Sequenziale: {throughput_seq:.2f} H/s\n")

    results_data = {"shared": [], "global": []}

    print(f"{'Cores':<6} | {'Architettura':<16} | {'Tempo (s)':<10} | {'Hash Rate (H/s)':<15}")
    print("-" * 75)

    with open(csv_filename, mode='w', newline='') as file_csv:
        writer = csv.writer(file_csv)
        writer.writerow(["Cores", "Architecture", "Time_Seconds", "Total_Attempts", "Hashes_Per_Second"])
        writer.writerow([1, "Sequential-Pure", f"{t_seq:.4f}", att_seq, f"{throughput_seq:.2f}"])

        for cores in core_configs:
            if cores > max_cores and cores != 1:
                continue 

            _, att_shared, t_shared = run_shared_nothing(
                target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=cores, scheduling="dynamic"
            )
            t_shared = max(t_shared, 0.0001)
            thr_shared = att_shared / t_shared
            results_data["shared"].append((cores, thr_shared))
            writer.writerow([cores, "Shared-Nothing", f"{t_shared:.4f}", att_shared, f"{thr_shared:.2f}"])
            print(f"{cores:<6} | {'Shared-Nothing':<16} | {t_shared:<10.4f} | {thr_shared:<15.2f}")
            file_csv.flush()

            _, att_global, t_global = run_global_exit(
                target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=cores
            )
            t_global = max(t_global, 0.0001)
            thr_global = att_global / t_global
            results_data["global"].append((cores, thr_global))
            writer.writerow([cores, "Global-Exit", f"{t_global:.4f}", att_global, f"{thr_global:.2f}"])
            print(f"{cores:<6} | {'Global-Exit':<16} | {t_global:<10.4f} | {thr_global:<15.2f}")
            file_csv.flush()

    print("-" * 75)
    print(f"Dati salvati in: {csv_filename}")

    try:
        import matplotlib.pyplot as plt
        cores_list = [row[0] for row in results_data["shared"]]
        ideal_throughput = [throughput_seq * c for c in cores_list]
        thr_shared = [row[1] for row in results_data["shared"]]
        thr_global = [row[1] for row in results_data["global"]]
        plt.figure(figsize=(11, 7))
        plt.plot(cores_list, ideal_throughput, 'k--', label='Throughput Ideale ($Baseline \\times N$)', linewidth=1.5)
        plt.axhline(y=throughput_seq, color='gray', linestyle='-.', label='Sequenziale Puro (Baseline Assoluta)', linewidth=2)
        
        plt.plot(cores_list, thr_shared, 's-', color='dodgerblue', label='Shared-Nothing (No IPC Lock)', linewidth=2)
        plt.plot(cores_list, thr_global, 'o-', color='crimson', label='Global Exit (IPC Lock)', linewidth=2)
        
        plt.title('Throughput Scaling: Potenza pura erogata dal sistema', fontsize=14)
        plt.xlabel('Numero di Core Logici', fontsize=12)
        plt.ylabel('Hashes per Second (H/s)', fontsize=12)
        plt.xticks(cores_list)
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.legend(fontsize=11)
        
        plt.ticklabel_format(style='plain', axis='y')
        
        plot_filename = "results/throughput_comparison_plot.png"
        plt.savefig(plot_filename, dpi=300)
        print(f"\nGrafico generato e salvato come: {plot_filename}")
        
    except ImportError:
        print("\nInstalla 'matplotlib' per generare il grafico.")

if __name__ == "__main__":
    main()
