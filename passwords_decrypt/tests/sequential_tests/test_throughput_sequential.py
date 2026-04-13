import sys
import os
import csv
from passlib.hash import des_crypt

# Configurazione del path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))

from crack_passwords_sequential import crack_passwords_sequential

def main():
    # Stesso carico della versione parallela
    passwords = [
        "18150615","18231122","18300704","18490530","18561201",
        "18681118","18720314","18860927","18941205","19070119",
        "19180522","19290610","19311203","19440716","19560228",
        "19680312","19790704","19851023","19991111","20180515"
    ]
    salt = "HX"
    start_y = 1800
    end_y = 2020
    
    print("Generazione degli hash target in corso...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in passwords]
    
    csv_filename = "results/throughput_sequential.csv"
    
    print("\n" + "="*70)
    print(" TEST THROUGHPUT SEQUENZIALE (BASELINE ASSOLUTA)")
    print("="*70)
    print(f"Spazio di ricerca: {start_y} - {end_y}")
    print("-" * 70)
    
    print("Esecuzione in corso (attendere)...")
    
    # Esecuzione
    _, attempts, elapsed = crack_passwords_sequential(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y
    )
    
    elapsed = max(elapsed, 0.0001)
    hash_rate = attempts / elapsed
    
    print("-" * 70)
    print(f"Risultati:")
    print(f"Tentativi totali: {attempts:,}")
    print(f"Tempo impiegato:  {elapsed:.4f} secondi")
    print(f"Hash Rate:        {hash_rate:.2f} H/s")
    print("-" * 70)
    
    # Salvataggio su CSV
    with open(csv_filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Mode", "Time_Seconds", "Total_Attempts", "Hashes_Per_Second"])
        writer.writerow(["sequential_pure", f"{elapsed:.4f}", attempts, f"{hash_rate:.2f}"])
        
    print(f"Dati salvati in: {csv_filename}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
