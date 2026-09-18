import json

with open("data/processed/project_timetable_filtered.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("="*70)
print("ROWS WITH ARRIVAL = None")
print("="*70)

count = 0

for row in data:
    if row.get("arrival") is None:
        print(row)
        count += 1
        if count == 10:
            break

print("\nTotal:", count)

print("\n" + "="*70)
print("ROWS WITH DEPARTURE = None")
print("="*70)

count = 0

for row in data:
    if row.get("departure") is None:
        print(row)
        count += 1
        if count == 10:
            break

print("\nTotal:", count)