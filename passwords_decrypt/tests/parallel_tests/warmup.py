import sys
import os
import multiprocessing

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src')))
from crack_passwords_parallel import crack_passwords

def warmup_system(target_hashes, salt):
    print("Esecuzione di Warm-up (Sustained Load per mitigazione Cold Start)...")
    crack_passwords(
        target_hashes, salt=salt, start_year=1980, end_year=2000, 
        cores=multiprocessing.cpu_count(), scheduling="dynamic"
    )
    
    print("Warm-up completato. Frequenze stabilizzate. Inizio misurazioni ufficiali.\n")
