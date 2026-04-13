import sys
import os
import multiprocessing
import csv
from passlib.hash import des_crypt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))

from crack_passwords_global import crack_passwords_global_exit
from warmup import warmup_system 

def main():
    dummy_passwords = ["10000101"]
    salt = "HX"
    print("Generazione degli hash fantasma in corso...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in dummy_passwords]
    
    workload_progression = [2, 4, 8, 16, 32, 64, 128, 256]
    end_y = 2020
    max_cores = multiprocessing.cpu_count()
    core_configs = [1, 2, 4, 8, 16, 20]
    
    csv_filename = "results/risultati_workload_global.csv"
    
    warmup_system(target_hashes, salt)

    print("\n" + "="*80)
    print(" AVVIO BENCHMARK GLOBAL EARLY EXIT (IPC) - WORKLOAD SCALING")
    print("="*80)
    print(f"Progressione Anni: {workload_progression}")
    print(f"Core massimi:      {max_cores}")
    print(f"File di output:    {csv_filename}")
    print("-" * 80)
    print(f"{'Anni Totali':<12} | {'Cores':<6} | {'Scheduling':<15} | {'Tempo (s)':<12} | {'Tentativi':<10}")
    print("-" * 80)

    with open(csv_filename, mode='w', newline='') as file_csv:
        writer = csv.writer(file_csv)
        writer.writerow(["Anni_Ricerca", "Cores", "Scheduling", "Tempo_s", "Tentativi"])

        for years in workload_progression:
            start_y = end_y - years + 1

            for cores in core_configs:
                if cores > max_cores and cores != 1:
                    continue 

                results, attempts, elapsed = crack_passwords_global_exit(
                    target_hashes,
                    salt=salt,
                    start_year=start_y,
                    end_year=end_y,
                    cores=cores
                )
                
                sched_label = "dynamic (IPC)"
                writer.writerow([years, cores, sched_label, f"{elapsed:.4f}", attempts])

                print(f"{years:<12} | {cores:<6} | {sched_label:<15} | {elapsed:<12.4f} | {attempts:<10}")
                file_csv.flush()
            print("-" * 80)

    print(f"Benchmark completato. Dati salvati in: {csv_filename}")

if __name__ == "__main__":
    main()
