import sys
import os
import multiprocessing
from passlib.hash import des_crypt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords as run_shared_nothing
from crack_passwords_global import crack_passwords_global_exit as run_global_exit
from warmup import warmup_system 

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
    test_cores = min(4, multiprocessing.cpu_count())
    warmup_system(target_hashes, salt)
   

    print("\n" + "="*75)
    print(" IL TEST SUICIDA: Shared-Nothing vs Global Early Exit")
    print("="*75)
    print(f"Password target:   {len(passwords)} (Tutte situate tra il 1815 e il 1830)")
    print(f"Spazio di ricerca: {start_y} - {end_y} (Molto oltre le password target)")
    print(f"Cores utilizzati:  {test_cores}")
    print(f"Scheduling:        Dynamic (Chunk=1)")
    print("-" * 75)
    
    print("\n[1] Esecuzione SHARED-NOTHING (Local Early Exit)...")
    _, att_local, t_local = run_shared_nothing(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=test_cores, scheduling="dynamic"
    )
    print(f"    -> Tentativi eseguiti: {att_local:,}")
    print(f"    -> Tempo impiegato:    {t_local:.4f} secondi")

    print("\n[2] Esecuzione GLOBAL EARLY EXIT (Memoria condivisa / IPC)...")
    _, att_global, t_global = run_global_exit(
        target_hashes, salt=salt, start_year=start_y, end_year=end_y, cores=test_cores
    )
    print(f"    -> Tentativi eseguiti: {att_global:,}")
    print(f"    -> Tempo impiegato:    {t_global:.4f} secondi")

    print("\n" + "="*75)
    print(" ANALISI DEL PARADOSSO")
    print("="*75)
    
    risparmio_calcoli = ((att_local - att_global) / att_local) * 100
    
    print(f"Il Global Exit ha risparmiato il {risparmio_calcoli:.1f}% dei calcoli (hash evitati).")
    
    if t_global > t_local:
        rallentamento = (t_global / t_local)
        print(f"TUTTAVIA, è risultato {rallentamento:.1f}x PIU' LENTO della versione Shared-Nothing!")
        print("\nCONCLUSIONE EMPIRICA PER IL REPORT:")
        print("L'overhead generato dalla comunicazione inter-processo (IPC), dai Lock e dalla")
        print("sincronizzazione del Manager.dict() supera di gran lunga il costo del")
        print("calcolo crittografico puro. In architetture multiprocessing Python,")
        print("l'approccio 'Shared-Nothing' è architetturalmente superiore.")
    else:
        print("Il Global Exit è stato più veloce (Il tuo PC ha un IPC incredibilmente ottimizzato!).")
        
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
