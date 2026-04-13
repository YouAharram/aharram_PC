import time
from passlib.hash import des_crypt
from utils import generate_dates

def crack_passwords_sequential(target_hashes, salt="HX", start_year=1950, end_year=2025):
    start_time = time.time()
    results = {h: None for h in target_hashes}
    remaining = set(target_hashes)
    attempts = 0
    
    for year in range(start_year, end_year + 1):
        for candidate in generate_dates(start_year=year, end_year=year):
            attempts += 1
            candidate_hash = des_crypt.using(salt=salt).hash(candidate)
            
            if candidate_hash in remaining:
                results[candidate_hash] = candidate
                remaining.remove(candidate_hash)
                
            if not remaining:
                break
                
        if not remaining:
            break
            
    elapsed = time.time() - start_time
    return results, attempts, elapsed
