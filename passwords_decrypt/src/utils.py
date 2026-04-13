from datetime import date, timedelta

def generate_dates(start_year=1950, end_year=2025):
    current = date(start_year, 1, 1)
    end = date(end_year, 12, 31)

    while current <= end:
        yield current.strftime("%Y%m%d")
        current += timedelta(days=1)
