import sys
import os
import csv
from passlib.hash import des_crypt

# Configurazione del path per importare dalla cartella 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))

from crack_passwords_sequential import crack_passwords_sequential
from warmup import warmup_system

def main():
    # ==========================================
    # 1. CONFIGURAZIONE DEL WORKLOAD CRESCENTE
    # ==========================================
    # Password fantasma per disabilitare l'early exit e testare il carico puro
    dummy_passwords = ["10000101"]
    salt = "HX"
    print("Generazione degli hash target fantasma in corso...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in dummy_passwords]
    
    # Stessa progressione usata nel test parallelo
    workload_progression = [2, 4, 8, 16, 32, 64, 128, 220,256]
    end_y = 2020
    
    # Nome del file di output separato
    csv_filename = "results/risultati_workload_sequential.csv"
    
    # Warm-up per stabilizzare la CPU
    warmup_system(target_hashes, salt)

    print("\n" + "="*80)
    print(" AVVIO BENCHMARK SEQUENZIALE: WORKLOAD SCALING (CARICO CRESCENTE)")
    print("="*80)
    print(f"Progressione Anni: {workload_progression}")
    print(f"File di output:    {csv_filename}")
    print("-" * 80)
    print(f"{'Anni Totali':<12} | {'Cores':<6} | {'Scheduling':<12} | {'Tempo (s)':<12} | {'Tentativi':<10}")
    print("-" * 80)

    # ==========================================
    # 2. ESECUZIONE E SCRITTURA CSV
    # ==========================================
    with open(csv_filename, mode='w', newline='') as file_csv:
        writer = csv.writer(file_csv)
        # Intestazione allineata a quella della matrice parallela
        writer.writerow(["Anni_Ricerca", "Cores", "Scheduling", "Tempo_s", "Tentativi"])

        for years in workload_progression:
            start_y = end_y - years + 1

            # Esecuzione
            _, attempts, elapsed = crack_passwords_sequential(
                target_hashes,
                salt=salt,
                start_year=start_y,
                end_year=end_y
            )

            # Parametri fissi per la baseline
            cores = 1
            sched = "sequential"

            # Salvataggio
            writer.writerow([years, cores, sched, f"{elapsed:.4f}", attempts])

            # Stampa a video
            print(f"{years:<12} | {cores:<6} | {sched:<12} | {elapsed:<12.4f} | {attempts:<10}")
            file_csv.flush()

    print("-" * 80)
    print(f"Benchmark completato. Dati salvati in: {csv_filename}")

if __name__ == "__main__":
    main()
