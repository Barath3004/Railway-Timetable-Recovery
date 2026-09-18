import json
from collections import Counter

with open("data/processed/project_timetable_filtered.json", "r", encoding="utf-8") as f:
    data = json.load(f)

arrival_errors = Counter()
departure_errors = Counter()

def valid(t):
    if t is None:
        return False

    t = str(t).strip()

    if t == "":
        return False

    if t.upper() in ["NA", "N/A", "--"]:
        return False

    return len(t.split(":")) in [2, 3]

for row in data:
    if not valid(row.get("arrival")):
        arrival_errors[str(row.get("arrival"))] += 1

    if not valid(row.get("departure")):
        departure_errors[str(row.get("departure"))] += 1

print("\nINVALID ARRIVALS")
print(arrival_errors)

print("\nINVALID DEPARTURES")
print(departure_errors)