"""
Inspect one train completely
"""

from pathlib import Path
import json

JSON_FILE = Path(
    r"C:\Users\barat\Desktop\Railway-Timetable-Recovery\data\raw\schedules.json"
)

TRAIN_NUMBER = "16317"


def main():

    with open(JSON_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    train = [
        row
        for row in data
        if row["train_number"] == TRAIN_NUMBER
    ]

    print("=" * 70)
    print("TRAIN DETAILS")
    print("=" * 70)

    print("Train Number :", TRAIN_NUMBER)
    print("Total Stops  :", len(train))

    print()

    for stop in train:
        print(
            stop["station_code"],
            stop["station_name"],
            "Arr:",
            stop["arrival"],
            "Dep:",
            stop["departure"],
            "Day:",
            stop["day"]
        )


if __name__ == "__main__":
    main()