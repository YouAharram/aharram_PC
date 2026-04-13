import sys
import os
import multiprocessing


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords


def warmup_system(target_hashes, salt):
    """
    Esegue un carico di lavoro a perdere (circa 1-2 secondi) per:
    1. Svegliare la CPU dai C-States e forzare il Turbo Boost prolungato.
    2. Costringere l'OS a inizializzare il Python multiprocessing e allocare memoria.
    3. Popolare le cache L1/L2/L3 della CPU.
    """
    print("Esecuzione di Warm-up (Sustained Load per mitigazione Cold Start)...")
    
    # Usiamo 20 anni di date (dal 1980 al 2000) per garantire che 
    # la CPU lavori al 100% per almeno un secondo intero.
    crack_passwords(
        target_hashes, salt=salt, start_year=1980, end_year=2000, 
        cores=multiprocessing.cpu_count(), scheduling="dynamic"
    )
    
    print("Warm-up completato. Frequenze stabilizzate. Inizio misurazioni ufficiali.\n")

