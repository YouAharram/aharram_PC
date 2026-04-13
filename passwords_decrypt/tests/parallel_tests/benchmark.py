import sys
import os
import multiprocessing
import csv
from passlib.hash import des_crypt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords
from warmup import warmup_system 

def main():
    dummy_passwords = ["10000101"]
    salt = "HX"
    print("Generazione degli hash target fantasma in corso...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in dummy_passwords]
    
    workload_progression = [2, 4, 8, 16, 32, 64, 128, 220, 256]
    end_y = 2020
    
    max_cores = multiprocessing.cpu_count()
    
    core_configs = [1, 2, 4, 8, 16]
    if max_cores not in core_configs and max_cores > 16:
        core_configs.append(max_cores)
        
    schedulings = ["static", "dynamic"]
    csv_filename = "results/risultati_matrix_scaling.csv"
    
    warmup_system(target_hashes, salt)

    print("\n" + "="*80)
    print(" AVVIO BENCHMARK MATRICE 3D: WORKLOAD x CORES x SCHEDULING")
    print("="*80)
    print(f"Progressione Anni: {workload_progression}")
    print(f"Cores da testare:  {core_configs}")
    print(f"File di output:    {csv_filename}")
    print("-" * 80)
    print(f"{'Anni Totali':<12} | {'Cores':<6} | {'Scheduling':<10} | {'Tempo (s)':<12} | {'Tentativi':<10}")
    print("-" * 80)

    with open(csv_filename, mode='w', newline='') as file_csv:
        writer = csv.writer(file_csv)
        writer.writerow(["Anni_Ricerca", "Cores", "Scheduling", "Tempo_s", "Tentativi"])

        for years in workload_progression:
            start_y = end_y - years + 1

            for cores in core_configs:
                if cores > max_cores and cores != 1:
                    continue 

                for sched in schedulings:
                    if cores == 1 and sched == "dynamic":
                        continue

                    results, attempts, elapsed = crack_passwords(
                        target_hashes,
                        salt=salt,
                        start_year=start_y,
                        end_year=end_y,
                        cores=cores,
                        scheduling=sched
                    )
                    
                    writer.writerow([years, cores, sched, f"{elapsed:.4f}", attempts])
                    label_sched = "baseline" if cores == 1 else sched
                    print(f"{years:<12} | {cores:<6} | {label_sched:<10} | {elapsed:<12.4f} | {attempts:<10}")
                    
                    file_csv.flush()
            
            print("-" * 80)

    print(f"Benchmark completato. Dataset multidimensionale salvato in: {csv_filename}")

if __name__ == "__main__":
    main()
