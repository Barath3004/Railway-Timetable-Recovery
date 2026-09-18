import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_cleaned.json"
)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

count = 0

for row in data:

    arrival = row.get("arrival")
    departure = row.get("departure")

    arr = str(arrival).strip()
    dep = str(departure).strip()

    if arr.lower() == "none" or dep.lower() == "none":
        print(row)
        count += 1

        if count >= 20:
            break

print("\nRows shown:", count)