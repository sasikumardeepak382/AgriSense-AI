
import pandas as pd
from pathlib import Path

# Project data folder
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "data" / "historical_2025"
OUTPUT_FILE = BASE_DIR / "data" / "market_prices_2025.csv"

all_data = []

# Read all 12 monthly CSV files
for file in INPUT_DIR.glob("*.csv"):

    print(f"Reading: {file.name}")

    df = pd.read_csv(file, skiprows=3, dtype=str, encoding="utf-8-sig")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Detect market name rows
    first_col = df.columns[0]

    market_rows = df[first_col].str.contains(
        "Market Name", case=False, na=False
    )

    df["market"] = None

    # Extract market names
    df.loc[market_rows, "market"] = (
        df.loc[market_rows, first_col]
        .str.replace("Market Name :", "", regex=False)
        .str.strip()
    )

    # Carry market name to following records
    df["market"] = df["market"].ffill()

    # Remove market heading rows
    df = df.loc[~market_rows].copy()

    # Standardize columns
    df = df.rename(columns={
        "Arrival Date": "arrival_date",
        "Arrivals (Metric Tonnes)": "arrivals",
        "Variety": "commodity",
        "Minimum Price (Rs./Quintal)": "min_price",
        "Maximum Price (Rs./Quintal)": "max_price",
        "Modal Price (Rs./Quintal)": "modal_price"
    })

    required = [
        "arrival_date", "arrivals", "commodity",
        "min_price", "max_price", "modal_price", "market"
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"{file.name}: Missing columns: {missing}"
        )

    df = df[required]

    all_data.append(df)

if not all_data:
    raise ValueError("No CSV files found!")

# Combine all months
master = pd.concat(all_data, ignore_index=True)

# Clean and convert values
master["arrival_date"] = pd.to_datetime(
    master["arrival_date"],
    dayfirst=True,
    errors="coerce"
)

for col in ["arrivals", "min_price", "max_price", "modal_price"]:
    master[col] = pd.to_numeric(master[col], errors="coerce")

master["commodity"] = master["commodity"].str.strip()
master["market"] = master["market"].str.strip()

# Remove invalid rows
master = master.dropna(
    subset=["arrival_date", "modal_price", "market"]
)

# Remove exact duplicate records
master = master.drop_duplicates()

# Save master CSV
master.to_csv(OUTPUT_FILE, index=False)

print("\nSUCCESS!")
print("Total records:", len(master))
print("Markets:", master["market"].nunique())
print("Commodities:", master["commodity"].nunique())
print("Date range:",
      master["arrival_date"].min(),
      "to",
      master["arrival_date"].max())
print("Saved at:", OUTPUT_FILE)
