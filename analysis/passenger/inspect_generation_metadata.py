import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

METADATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger_ml"
    / "generation_metadata.json"
)


def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_dict(data, indent=0):
    prefix = " " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}{key}:")
                print_dict(value, indent + 4)
            else:
                print(f"{prefix}{key}: {value}")

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                print_dict(item, indent + 4)
            else:
                print(f"{prefix}- {item}")

    else:
        print(f"{prefix}{data}")


def main():
    print_section("GENERATION METADATA INSPECTION")

    print(f"Project root : {PROJECT_ROOT}")
    print(f"Metadata file: {METADATA_FILE}")

    if not METADATA_FILE.exists():
        print("\nERROR: generation_metadata.json was not found.")
        return

    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"\nERROR: Could not read JSON: {e}")
        return

    print("\nJSON loaded successfully.")

    print_section("FULL METADATA")

    print_dict(metadata)

    # ---------------------------------------------------------
    # Search recursively for important keys
    # ---------------------------------------------------------

    important_keywords = [
        "time",
        "weight",
        "load",
        "service",
        "share",
        "disruption",
        "factor",
        "severity",
        "priority",
        "noise",
        "delay",
        "duration",
        "train_count",
        "target",
        "feature",
        "formula",
        "seed",
        "split",
    ]

    found = {}

    def recursive_search(obj, path="root"):
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()

                if any(keyword in key_lower for keyword in important_keywords):
                    found[f"{path}.{key}"] = value

                recursive_search(value, f"{path}.{key}")

        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                recursive_search(value, f"{path}[{index}]")

    recursive_search(metadata)

    print_section("IMPORTANT PARAMETERS FOUND")

    if not found:
        print("No matching parameters were automatically detected.")
    else:
        for path, value in found.items():
            print(f"\n{path}:")
            if isinstance(value, (dict, list)):
                print(json.dumps(value, indent=4, ensure_ascii=False))
            else:
                print(value)

    # ---------------------------------------------------------
    # Explicitly inspect likely time weights
    # ---------------------------------------------------------

    print_section("TIME WEIGHT CHECK")

    def find_time_weights(obj, path="root"):
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()

                if "weight" in key_lower and isinstance(value, (dict, list)):
                    print(f"\nPossible weight field: {path}.{key}")
                    print(json.dumps(value, indent=4, ensure_ascii=False))

                    if isinstance(value, dict):
                        numeric_values = []

                        for v in value.values():
                            if isinstance(v, (int, float)):
                                numeric_values.append(float(v))

                        if numeric_values:
                            total = sum(numeric_values)

                            print(f"\nNumeric weight count: {len(numeric_values)}")
                            print(f"Actual sum: {total:.10f}")

                            if abs(total - 1.0) < 1e-6:
                                print("STATUS: PASS - weights sum to 1.0")
                            else:
                                print("STATUS: CHECK - weights do not sum exactly to 1.0")

                find_time_weights(value, f"{path}.{key}")

        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                find_time_weights(value, f"{path}[{index}]")

    find_time_weights(metadata)

    # ---------------------------------------------------------
    # Top-level metadata summary
    # ---------------------------------------------------------

    print_section("TOP-LEVEL KEYS")

    if isinstance(metadata, dict):
        for key in metadata:
            print(f"- {key}")

    print_section("INSPECTION COMPLETE")

    print(
        "\nCopy the terminal output from "
        "'IMPORTANT PARAMETERS FOUND' and 'TIME WEIGHT CHECK' "
        "and send that output here."
    )


if __name__ == "__main__":
    main()