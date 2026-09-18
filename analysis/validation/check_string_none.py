import json

with open("data/processed/project_timetable_filtered.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 70)
print("ARRIVAL == 'None'")
print("=" * 70)

count = 0

for row in data:

    if str(row.get("arrival")).strip() == "None":

        print(row)

        count += 1

        if count == 10:
            break

print("\nTotal Found :", count)

print("\n" + "=" * 70)
print("DEPARTURE == 'None'")
print("=" * 70)

count = 0

for row in data:

    if str(row.get("departure")).strip() == "None":

        print(row)

        count += 1

        if count == 10:
            break

print("\nTotal Found :", count)