import sys
import os
import multiprocessing
import csv
import matplotlib.pyplot as plt
from passlib.hash import des_crypt
from warmup import warmup_system

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_sequential import crack_passwords_sequential
from crack_passwords_parallel import crack_passwords

def main():
    dummy_passwords = ["10000101"] 
    salt = "HX"
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in dummy_passwords]
    workload_years = [1, 2, 4, 8, 15, 30, 60]
    
    end_y = 2020
    test_cores = min(20, multiprocessing.cpu_count())
    csv_filename = "crossover_data.csv"

    warmup_system(target_hashes, salt)
    
    print("\n" + "="*70)
    print(" ANALISI DEL CROSSOVER POINT (SEQUENTIAL vs PARALLEL)")
    print(" Alla ricerca del costo di 'Startup' del Multiprocessing")
    print("="*70)
    print(f"Cores Paralleli: {test_cores}")
    print("-" * 70)
    print(f"{'Anni':<6} | {'Hash Totali':<12} | {'Tempo Seq (s)':<15} | {'Tempo Par (s)':<15}")
    print("-" * 70)

    results_seq = []
    results_par = []
    
    with open(csv_filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Workload_Years", "Total_Hashes", "Time_Sequential", "Time_Parallel"])

        for years in workload_years:
            start_y = end_y - years + 1
            
            _, att_seq, t_seq = crack_passwords_sequential(
                target_hashes, salt=salt, start_year=start_y, end_year=end_y
            )
            
            _, att_par, t_par = crack_passwords(
                target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=test_cores, scheduling="dynamic"
            )
            
            results_seq.append(t_seq)
            results_par.append(t_par)
            
            writer.writerow([years, att_seq, f"{t_seq:.4f}", f"{t_par:.4f}"])
            print(f"{years:<6} | {att_seq:<12} | {t_seq:<15.4f} | {t_par:<15.4f}")
            f.flush()

    print("-" * 70)
    print("Test completato. Generazione grafico in corso...")

    plt.figure(figsize=(10, 6))
    
    plt.plot(workload_years, results_seq, 'b-o', label='Esecuzione Sequenziale', linewidth=2)
    plt.plot(workload_years, results_par, 'r-o', label=f'Esecuzione Parallela ({test_cores} Cores)', linewidth=2)
    plt.fill_between(workload_years, results_seq, results_par, 
                     where=[results_seq[i] < results_par[i] for i in range(len(workload_years))], 
                     interpolate=True, color='blue', alpha=0.1, label='Overhead (Sequenziale vince)')
    
    plt.fill_between(workload_years, results_seq, results_par, 
                     where=[results_seq[i] >= results_par[i] for i in range(len(workload_years))], 
                     interpolate=True, color='red', alpha=0.1, label='Speedup (Parallelo vince)')

    plt.title('Crossover Point: Costo di Startup vs Beneficio Parallelo')
    plt.xlabel('Anni di date da scansionare')
    plt.ylabel('Tempo di esecuzione (Secondi)')
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend()
    
    plot_filename = "crossover_plot.png"
    plt.savefig(plot_filename, dpi=300)
    print(f"Grafico salvato: {plot_filename}\n")

if __name__ == "__main__":
    main()
