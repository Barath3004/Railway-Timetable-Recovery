import pandas as pd

FILE = "data/processed/passenger/passenger_statistics.csv"

df = pd.read_csv(FILE)

print()
print("=" * 55)
print("        PASSENGER DATASET ANALYSIS")
print("=" * 55)

print(f"Total records: {len(df)}")
print(f"Total columns: {len(df.columns)}")

print()
print("=== COLUMNS ===")
print(df.columns.tolist())

print()
print("=== MISSING VALUES ===")
missing = df.isna().sum()

for col in df.columns:
    print(f"{col:20} : {missing[col]} missing")

print()
print("=== PASSENGER DATA AVAILABILITY ===")

print(
    "Annual passengers available:",
    df["annual_passengers"].notna().sum()
)

print(
    "Daily passengers available:",
    df["daily_passengers"].notna().sum()
)

print(
    "Footfall available:",
    df["footfall"].notna().sum()
)

print()
print("=== COMBINATION OF PASSENGER DATA ===")

print(
    "Annual + Daily:",
    (
        df["annual_passengers"].notna()
        & df["daily_passengers"].notna()
    ).sum()
)

print(
    "Annual only:",
    (
        df["annual_passengers"].notna()
        & df["daily_passengers"].isna()
    ).sum()
)

print(
    "Daily only:",
    (
        df["annual_passengers"].isna()
        & df["daily_passengers"].notna()
    ).sum()
)

print(
    "Neither annual nor daily:",
    (
        df["annual_passengers"].isna()
        & df["daily_passengers"].isna()
    ).sum()
)

print()
print("=== CATEGORY DISTRIBUTION ===")
print(df["category"].value_counts(dropna=False).to_string())

print()
print("=== DAILY PASSENGERS BY CATEGORY ===")

category_stats = (
    df.groupby("category")["daily_passengers"]
    .agg(
        count="count",
        mean="mean",
        median="median",
        minimum="min",
        maximum="max"
    )
    .round(2)
)

print(category_stats.to_string())

print()
print("=== ANNUAL → DAILY CONSISTENCY ===")

check = df[
    df["annual_passengers"].notna()
    & df["daily_passengers"].notna()
].copy()

check["calculated_daily"] = (
    check["annual_passengers"] / 365
)

check["difference"] = (
    check["daily_passengers"]
    - check["calculated_daily"]
)

check["difference_percent"] = (
    check["difference"].abs()
    / check["calculated_daily"]
    * 100
)

print(
    "Records with both annual and daily:",
    len(check)
)

print(
    "Mean difference:",
    round(check["difference"].mean(), 2)
)

print(
    "Median difference:",
    round(check["difference"].median(), 2)
)

print(
    "Mean absolute difference %:",
    round(check["difference_percent"].mean(), 2)
)

print()
print("=== LARGEST ANNUAL/DAILY DIFFERENCES ===")

print(
    check[
        [
            "station_code",
            "category",
            "annual_passengers",
            "daily_passengers",
            "calculated_daily",
            "difference_percent"
        ]
    ]
    .sort_values("difference_percent", ascending=False)
    .head(20)
    .to_string(index=False)
)

print()
print("=== PASSENGER RANGE ===")

print(
    "Minimum daily passengers:",
    df["daily_passengers"].min()
)

print(
    "Maximum daily passengers:",
    df["daily_passengers"].max()
)

print(
    "Median daily passengers:",
    df["daily_passengers"].median()
)

print(
    "Mean daily passengers:",
    round(df["daily_passengers"].mean(), 2)
)

print()
print("=" * 55)
print("       ANALYSIS COMPLETE")
print("=" * 55)