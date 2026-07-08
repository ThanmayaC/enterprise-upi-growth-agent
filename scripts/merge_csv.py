from pathlib import Path
import csv

# Root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Folder containing the transaction CSVs
INPUT_DIR = PROJECT_ROOT / "scripts" / "dataset_generator" / "fact"

# Output file
OUTPUT_FILE = PROJECT_ROOT / "data" / "transactions.csv"

csv_files = sorted(INPUT_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError(f"No CSV files found in {INPUT_DIR}")

print(f"Found {len(csv_files)} CSV files.\n")

expected_columns = None
merged_rows = []

for csv_file in csv_files:
    print(f"Reading: {csv_file.name}")

    with csv_file.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"No header found in {csv_file.name}")

        # Validate schema
        if expected_columns is None:
            expected_columns = reader.fieldnames
        elif reader.fieldnames != expected_columns:
            raise ValueError(f"Column mismatch detected in {csv_file.name}")

        # Read all rows
        for row in reader:
            merged_rows.append(row)

# Remove duplicates
before = len(merged_rows)

seen = set()
unique_rows = []

for row in merged_rows:
    key = tuple(row[col] for col in expected_columns)

    if key not in seen:
        seen.add(key)
        unique_rows.append(row)

after = len(unique_rows)

# Create output folder
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Write merged CSV
with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=expected_columns)
    writer.writeheader()
    writer.writerows(unique_rows)

print("\n" + "=" * 60)
print("Merge completed successfully!")
print("=" * 60)
print(f"Files merged      : {len(csv_files)}")
print(f"Rows before dedup : {before:,}")
print(f"Rows after dedup  : {after:,}")
print(f"Columns           : {len(expected_columns)}")
print(f"Output saved to   : {OUTPUT_FILE}")