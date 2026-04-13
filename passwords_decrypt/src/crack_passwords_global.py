import time
import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from passlib.hash import des_crypt
from utils import generate_dates

def _crack_single_year_global(args):
    target_hashes, salt, year, shared_remaining = args
    results = {h: None for h in target_hashes}
    attempts = 0
    
    start_t = time.time()
    pid = os.getpid()
    
    for candidate in generate_dates(start_year=year, end_year=year):
        attempts += 1
        
        if len(shared_remaining) == 0:
            break
            
        candidate_hash = des_crypt.using(salt=salt).hash(candidate)
        
        if candidate_hash in shared_remaining:
            results[candidate_hash] = candidate
            
            try:
                del shared_remaining[candidate_hash]
            except KeyError:
                pass
                
        if len(shared_remaining) == 0:
            break
            
    end_t = time.time()
    
    return results, attempts, pid, start_t, end_t


def crack_passwords_global_exit(target_hashes, salt="HX", start_year=1950, end_year=2025, cores=4, return_profile=False):
    start_time = time.time()
    manager = multiprocessing.Manager()
    shared_remaining = manager.dict({h: True for h in target_hashes})
    years = list(range(start_year, end_year + 1))
    tasks = [(target_hashes, salt, year, shared_remaining) for year in years]
    
    final_results = {h: None for h in target_hashes}
    total_attempts = 0
    profiling_log = []
    
    with ProcessPoolExecutor(max_workers=cores) as executor:
        results_list = list(executor.map(_crack_single_year_global, tasks, chunksize=1))
        
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
