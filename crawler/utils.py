import re

def parse_career_range(career_str: str) -> tuple[int, int]:
    if not career_str or "신입" in career_str:
        min_career = 0
        max_career_match = re.search(r'(\d+)', career_str)
        max_career = int(max_career_match.group(1)) if max_career_match else 0
        return min_career, max_career

    range_match = re.search(r'(\d+)[년\s]*[-~][\s]*(\d+)', career_str)
    single_match = re.search(r'(\d+)', career_str)

    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    elif "이상" in career_str and single_match:
        return int(single_match.group(1)), 99
    elif single_match:
        year = int(single_match.group(1))
        return year, year
    return 0, 99

def parse_location(location_str):
    parts = location_str.strip().split()
    region = parts[0] if len(parts) > 0 else None
    district = parts[1] if len(parts) > 1 else None

    return {
        "region": region,
        "district": district,
    }