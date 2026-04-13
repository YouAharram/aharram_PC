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
    passwords = [
        "18150615","18231122","18300704","18490530","18561201",
        "18681118","18720314","18860927","18941205","19070119",
        "19180522","19290610","19311203","19440716","19560228",
        "19680312","19790704","19851023","19991111","20180515"
    ]
    salt = "HX"
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in passwords]
    
    start_y = 1800
    end_y = 2020
    total_years = end_y - start_y + 1 # 221 anni totali
    
    test_cores = min(4, multiprocessing.cpu_count()) 
    chunk_sizes = [1, 2, 5, 10, 20, 50, 110, 221]
    csv_filename = "results/granularity_data.csv"
    
    warmup_system(target_hashes, salt)

    print("\n" + "="*70)
    print(" TEST DI GRANULARITA' (CHUNK SIZE TUNING)")
    print("="*70)
    print(f"Core fisici utilizzati: {test_cores}")
    print(f"Task totali (anni):     {total_years}")
    print(f"File output:            {csv_filename}")
    print("-" * 70)
    print(f"{'Chunk Size':<12} | {'Tempo (s)':<12} | {'Tentativi':<10}")
    print("-" * 70)

    with open(csv_filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Chunk_Size", "Time_Seconds", "Total_Attempts"])

        for chunk in chunk_sizes:
            _, attempts, elapsed = crack_passwords(
                target_hashes, 
                salt=salt, 
                start_year=start_y, 
                end_year=end_y, 
                cores=test_cores, 
                scheduling="custom",  
                custom_chunksize=chunk
            )
            
            writer.writerow([chunk, f"{elapsed:.4f}", attempts])
            print(f"{chunk:<12} | {elapsed:<12.4f} | {attempts:<10}")
            f.flush()

    print("-" * 70)
    print("Test completato. Cerca il 'punto di minimo' nei tempi salvati.")

if __name__ == "__main__":
    main()
