import sys
import os
import time
import multiprocessing
import csv
from passlib.hash import des_crypt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords
from warmup import warmup_system 

def main():
    dummy_passwords = ["10000101", "10000202", "10000303"]
    salt = "HX"
    
    print("Generazione hash target fantasma per il Weak Scaling...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in dummy_passwords]
    years_per_core = 10 
    end_y = 2020 # Anno finale fisso, l'anno iniziale andrà a ritroso
    max_cores = multiprocessing.cpu_count()
    core_configs = [1, 2, 4, 8, 16, 20]
    schedulings = ["static", "dynamic"]
    csv_filename = "weak_scaling_data.csv"
    warmup_system(target_hashes, salt)
 
    print("\n" + "="*70)
    print(" TEST WEAK SCALING: CARICO PROPORZIONALE AI CORE")
    print(" (Obiettivo: Il tempo dovrebbe rimanere costante)")
    print("="*70)
    print(f"Carico per singolo core: {years_per_core} anni")
    print(f"File output:             {csv_filename}")
    print("-" * 70)
    print(f"{'Cores':<6} | {'Scheduling':<10} | {'Anni Totali':<12} | {'Tempo (s)':<10} | {'Efficienza':<10}")
    print("-" * 70)

    t1_times = {"static": None, "dynamic": None}

    with open(csv_filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Cores", "Scheduling", "Total_Years", "Time_Seconds", "Efficiency_perc"])

        for cores in core_configs:
            if cores > max_cores and cores != 1:
                continue

            total_years = years_per_core * cores
            start_y = end_y - total_years + 1

            for sched in schedulings:
                _, _, elapsed = crack_passwords(
                    target_hashes, 
                    salt=salt, 
                    start_year=start_y, 
                    end_year=end_y, 
                    cores=cores, 
                    scheduling=sched
                )
                
                if cores == 1:
                    t1_times[sched] = elapsed
                    efficiency = 100.0
                else:
                    efficiency = (t1_times[sched] / elapsed) * 100
                
                writer.writerow([cores, sched, total_years, f"{elapsed:.4f}", f"{efficiency:.1f}"])
                print(f"{cores:<6} | {sched:<10} | {total_years:<12} | {elapsed:<10.4f} | {efficiency:<9.1f}%")
                f.flush()

    print("-" * 70)
    print("Test completato.")

if __name__ == "__main__":
    main()
