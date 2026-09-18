import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_cleaned.json"
)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

arrival_counter = Counter()
departure_counter = Counter()

for row in data:

    arrival = str(row.get("arrival")).strip()

    if arrival != "None":
        try:
            h, m, s = arrival.split(":")
            int(h)
            int(m)
            int(s)
        except:
            arrival_counter[arrival] += 1

    departure = str(row.get("departure")).strip()

    if departure != "None":
        try:
            h, m, s = departure.split(":")
            int(h)
            int(m)
            int(s)
        except:
            departure_counter[departure] += 1

print("\nINVALID ARRIVAL VALUES")
print("=" * 60)

for value, count in arrival_counter.most_common():
    print(value, "->", count)

print("\nINVALID DEPARTURE VALUES")
print("=" * 60)

for value, count in departure_counter.most_common():
    print(value, "->", count)