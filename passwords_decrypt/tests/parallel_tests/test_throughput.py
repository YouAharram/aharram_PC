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
    print("Generazione degli hash target in corso...")
    target_hashes = [des_crypt.using(salt=salt).hash(p) for p in passwords]
    
    start_y = 1800
    end_y = 2020
    
    max_cores = multiprocessing.cpu_count()
    core_configs = [1, 2, 4, 8, 16, 20]
    schedulings = ["static", "dynamic"]
    
    csv_filename = "results/throughput_data.csv"
    warmup_system(target_hashes, salt)
   
    print("\n" + "="*70)
    print(" TEST DI THROUGHPUT (HASH RATE)")
    print(" (Misurazione della potenza pura: Hashes per Second)")
    print("="*70)

    print("Calcolo della Baseline (1 Core) per il Throughput Ideale...")
    _, attempts_1c, time_1c = crack_passwords(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=1, scheduling="dynamic"
    )
    
    time_1c = max(time_1c, 0.0001) 
    baseline_throughput = attempts_1c / time_1c
    print(f"Throughput Baseline (1 Core): {baseline_throughput:.2f} H/s\n")
    results_data = {"static": [], "dynamic": []}

    print(f"{'Cores':<6} | {'Scheduling':<10} | {'Tempo (s)':<10} | {'Hash Rate (H/s)':<15}")
    print("-" * 70)

    with open(csv_filename, mode='w', newline='') as file_csv:
        writer = csv.writer(file_csv)
        writer.writerow(["Cores", "Scheduling", "Time_Seconds", "Total_Attempts", "Hashes_Per_Second"])
        writer.writerow([1, "baseline", f"{time_1c:.4f}", attempts_1c, f"{baseline_throughput:.2f}"])

        for cores in core_configs:
            if cores > max_cores and cores != 1:
                continue 

            for sched in schedulings:
                if cores == 1:
                    results_data[sched].append((1, baseline_throughput))
                    if sched == "dynamic":
                        print(f"{1:<6} | {'baseline':<10} | {time_1c:<10.4f} | {baseline_throughput:<15.2f}")
                    continue
                _, attempts, elapsed = crack_passwords(
                    target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=cores, scheduling=sched
                )
                
                elapsed = max(elapsed, 0.0001)
                throughput = attempts / elapsed
                
                results_data[sched].append((cores, throughput))
                writer.writerow([cores, sched, f"{elapsed:.4f}", attempts, f"{throughput:.2f}"])
                print(f"{cores:<6} | {sched:<10} | {elapsed:<10.4f} | {throughput:<15.2f}")
                file_csv.flush()

    print("-" * 70)
    print(f"Dati salvati in: {csv_filename}")

    try:
        import matplotlib.pyplot as plt
        cores_list = [row[0] for row in results_data["dynamic"]]
        ideal_throughput = [baseline_throughput * c for c in cores_list]
        throughput_static = [row[1] for row in results_data["static"]]
        throughput_dynamic = [row[1] for row in results_data["dynamic"]]
        plt.figure(figsize=(10, 6))
        plt.plot(cores_list, ideal_throughput, 'k--', label='Throughput Ideale (Lineare)')
        
        plt.plot(cores_list, throughput_static, 'b-o', label='Static Scheduling')
        plt.plot(cores_list, throughput_dynamic, 'r-o', label='Dynamic Scheduling')
        
        plt.title('Throughput Scaling: Potenza di Decrittazione (H/s)')
        plt.xlabel('Numero di Core')
        plt.ylabel('Hashes per Second (H/s)')
        plt.xticks(cores_list)
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.legend()
        plt.ticklabel_format(style='plain', axis='y')
        plot_filename = "results/throughput_plot.png"
        plt.savefig(plot_filename)
        print(f"\nGrafico generato e salvato come: {plot_filename}")
        
    except ImportError:
        print("\nNota: Installa 'matplotlib' per generare automaticamente il grafico.")

if __name__ == "__main__":
    main()
