import sys
import os
import time
import multiprocessing
import csv
from passlib.hash import des_crypt
from warmup import warmup_system 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords

def main():
    passwords = [
        "18150615","18231122","18300704","18490530","18561201",
        "18681118","18720314","18860927","18941205","19070119",
        "19180522","19290610","19311203","19440716","19560228",
        "19680312","19790704","19851023","19991111","20180515"
    ]
    
    salt = "HX"
    print("Generazione hash target...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in passwords]
    
    start_y = 1800
    end_y = 2020
    
    max_cores = multiprocessing.cpu_count()
    core_configs = [1, 2, 4, 8, 16, 20]
    schedulings = ["static", "dynamic"]
    
    csv_filename = "results/strong_scaling_data.csv"
    warmup_system(target_hashes, salt)

    print("\n" + "="*60)
    print(" TEST STRONG SCALING: TEMPI E TENTATIVI")
    print("="*60)
    print(f"File output: {csv_filename}")
    print("-" * 60)
    print(f"{'Cores':<6} | {'Scheduling':<10} | {'Tempo (s)':<12} | {'Tentativi':<10}")
    print("-" * 60)

    with open(csv_filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Cores", "Scheduling", "Time_Seconds", "Total_Attempts"])

        for cores in core_configs:
            if cores > max_cores and cores != 1:
                continue

            for sched in schedulings:
                _, attempts, elapsed = crack_passwords(
                    target_hashes, 
                    salt=salt, 
                    start_year=start_y, 
                    end_year=end_y, 
                    cores=cores, 
                    scheduling=sched
                )
                
                writer.writerow([cores, sched, f"{elapsed:.4f}", attempts])
                print(f"{cores:<6} | {sched:<10} | {elapsed:<12.4f} | {attempts:<10}")
                f.flush()

    print("-" * 60)
    print("Test completato.")

if __name__ == "__main__":
    main()
