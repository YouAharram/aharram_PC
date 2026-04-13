import time
import os
from concurrent.futures import ProcessPoolExecutor
from passlib.hash import des_crypt
from utils import generate_dates

def _crack_single_year(args):
    target_hashes, salt, year = args
    results = {h: None for h in target_hashes}
    remaining = set(target_hashes)
    attempts = 0
    
    start_t = time.time()
    pid = os.getpid()
    
    for candidate in generate_dates(start_year=year, end_year=year):
        attempts += 1
        candidate_hash = des_crypt.using(salt=salt).hash(candidate)
        
        if candidate_hash in remaining:
            results[candidate_hash] = candidate
            remaining.remove(candidate_hash)
            
        if not remaining:
            break
            
    end_t = time.time()
    
    return results, attempts, pid, start_t, end_t

def crack_passwords(target_hashes, salt="HX", start_year=1950, end_year=2025, cores=4, scheduling="dynamic", custom_chunksize=None, return_profile=False):
    start_time = time.time()
    
    years = list(range(start_year, end_year + 1))
    tasks = [(target_hashes, salt, year) for year in years]
    
    if scheduling not in ["static", "dynamic", "custom"]:
        raise ValueError("Il parametro scheduling deve essere 'static', 'dynamic' o 'custom'")
        
    if custom_chunksize is not None:
        calc_chunksize = custom_chunksize
    elif scheduling == "static":
        calc_chunksize = max(1, len(tasks) // cores) 
    else: 
        calc_chunksize = 1

    final_results = {h: None for h in target_hashes}
    total_attempts = 0
    profiling_log = []
    
    with ProcessPoolExecutor(max_workers=cores) as executor:
        results_list = list(executor.map(_crack_single_year, tasks, chunksize=calc_chunksize))
        
    for partial_results, partial_attempts, pid, t_start, t_end in results_list:
        total_attempts += partial_attempts
        
        if return_profile:
            profiling_log.append((pid, t_start, t_end))
            
        for h, pw in partial_results.items():
            if pw is not None and final_results[h] is None:
                final_results[h] = pw

    elapsed = time.time() - start_time
    
    if return_profile:
        return final_results, total_attempts, elapsed, profiling_log
    
    return final_results, total_attempts, elapsed
