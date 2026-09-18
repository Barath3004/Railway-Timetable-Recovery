import json
import os

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "station",
    "station_platform_profile.json"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("VALIDATE STATION PLATFORM PROFILE")
print("=" * 70)

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    stations = json.load(file)

print(f"Loaded Stations : {len(stations)}")

# ==========================================================
# VARIABLES
# ==========================================================

invalid_platform_numbers = 0
duplicate_platform_numbers = 0
invalid_split = 0
invalid_buffer = 0
invalid_platform_type = 0

mainline_total = 0
suburban_total = 0

VALID_TYPES = {
    "MAINLINE",
    "SUBURBAN"
}

# ==========================================================
# BUFFER RULE
# ==========================================================

def expected_buffer(platforms):

    if platforms <= 4:
        return 5

    elif platforms <= 8:
        return 10

    elif platforms <= 12:
        return 15

    elif platforms <= 16:
        return 20

    return 25

# ==========================================================
# VALIDATION
# ==========================================================

for station in stations:

    total = station["platforms_total"]

    platforms = station["platforms"]

    numbers = []

    mainline = 0
    suburban = 0

    # -----------------------------
    # Platform checks
    # -----------------------------

    for p in platforms:

        num = p["platform_number"]
        ptype = p["platform_type"]

        numbers.append(num)

        if ptype == "MAINLINE":
            mainline += 1
            mainline_total += 1

        elif ptype == "SUBURBAN":
            suburban += 1
            suburban_total += 1

        else:
            invalid_platform_type += 1

    # -----------------------------
    # Duplicate platform numbers
    # -----------------------------

    if len(numbers) != len(set(numbers)):
        duplicate_platform_numbers += 1

    # -----------------------------
    # Continuous numbering
    # -----------------------------

    expected = list(range(1, total + 1))

    if sorted(numbers) != expected:
        invalid_platform_numbers += 1

    # -----------------------------
    # Split validation
    # -----------------------------

    if (mainline + suburban) != total:
        invalid_split += 1

    # -----------------------------
    # Buffer validation
    # -----------------------------

    if station["station_buffer_minutes"] != expected_buffer(total):
        invalid_buffer += 1

    # -----------------------------
    # 4 Platform Rule
    # -----------------------------

    if total == 4:

        if not (mainline == 3 and suburban == 1):

            print(
                f"4 Platform Rule Failed : {station['station_code']}"
            )

    # -----------------------------
    # <=3 Platform Rule
    # -----------------------------

    if total <= 3:

        if suburban != 0:

            print(
                f"<=3 Platform Rule Failed : {station['station_code']}"
            )

# ==========================================================
# SUMMARY
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Invalid Platform Numbering : {invalid_platform_numbers}")
print(f"Duplicate Platform Numbers : {duplicate_platform_numbers}")
print(f"Invalid Platform Split     : {invalid_split}")
print(f"Invalid Buffer             : {invalid_buffer}")
print(f"Invalid Platform Type      : {invalid_platform_type}")

print()

print(f"Total MAINLINE Platforms : {mainline_total}")
print(f"Total SUBURBAN Platforms : {suburban_total}")
print(f"Total Platforms          : {mainline_total + suburban_total}")

print()

print("=" * 70)

if (
    invalid_platform_numbers == 0
    and duplicate_platform_numbers == 0
    and invalid_split == 0
    and invalid_buffer == 0
    and invalid_platform_type == 0
):
    print("VALIDATION PASSED")
else:
    print("VALIDATION FAILED")

print("=" * 70)