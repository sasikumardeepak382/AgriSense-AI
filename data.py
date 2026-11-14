from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "market_prices.csv"
HISTORICAL_FILE = ROOT / "data" / "historical_prices.csv"
HISTORICAL_2025_FILE = ROOT / "data" / "market_prices_2025.csv"
ALIASES = {
 "date": ["date","arrival_date","arrivaldate","reported_date"],
 "commodity": ["commodity","commodity_name"], "market": ["market","market_name"],
 "district": ["district","district_name"], "state": ["state","state_name"],
 "min_price": ["min_price","minimum_price","min_x0020_price"],
 "max_price": ["max_price","maximum_price","max_x0020_price"],
 "modal_price": ["modal_price","modalprice","modal_x0020_price"],
 "arrival": ["arrival","arrivals","arrivals_tonnes","quantity"]
}

def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    df=raw.copy()
    original=list(df.columns)
    df.columns=[str(c).strip().lower().replace(" ","_") for c in df.columns]
    ren={}
    for target, opts in ALIASES.items():
        for c in df.columns:
            if c in opts: ren[c]=target; break
    df=df.rename(columns=ren)
    required=["date","commodity","market","min_price","max_price","modal_price"]
    missing=[x for x in required if x not in df.columns]
    if missing: raise ValueError("Missing columns: "+", ".join(missing)+". Original columns: "+", ".join(original))
    for c in ["state","district","arrival"]:
        if c not in df: df[c]=None
    df["date"] = pd.to_datetime(
    df["date"],
    errors="coerce",
    format="mixed",
    dayfirst=False
)
    for c in ["min_price","max_price","modal_price","arrival"]:
        df[c]=pd.to_numeric(df[c].astype(str).str.replace(",","",regex=False),errors="coerce")
    for c in ["commodity","market","district","state"]:
        df[c]=df[c].fillna("Unknown").astype(str).str.strip()
    df=df.dropna(subset=["date","modal_price"])
    df=df[(df.modal_price>0)&(df.min_price>=0)&(df.max_price>=0)]
    return df.sort_values("date").reset_index(drop=True)

def load_data():
    if not DATA_FILE.exists(): return pd.DataFrame(columns=["date","commodity","market","district","state","min_price","max_price","modal_price","arrival"])
    return normalize(pd.read_csv(DATA_FILE))

def save_upload(file_bytes: bytes):
    import io
    raw=pd.read_csv(io.BytesIO(file_bytes))
    df=normalize(raw)
    DATA_FILE.parent.mkdir(exist_ok=True)
    raw.to_csv(DATA_FILE,index=False)
    return df

def vegetable_names(df):
    return sorted(df.commodity.dropna().unique().tolist())
def load_historical_data():
    if not HISTORICAL_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(HISTORICAL_FILE)

    df["date"] = pd.to_datetime(
    df["date"],
    errors="coerce",
    dayfirst=True
)
    df["average_price"] = pd.to_numeric(
        df["average_price"], errors="coerce"
    )

    df = df.dropna(subset=["date", "average_price"])
    return df.sort_values("date").reset_index(drop=True)

def load_2025_data():
    if not HISTORICAL_2025_FILE.exists():
        return pd.DataFrame()

    raw = pd.read_csv(HISTORICAL_2025_FILE)

    df = normalize(raw)

    return df.sort_values("date").reset_index(drop=True)
