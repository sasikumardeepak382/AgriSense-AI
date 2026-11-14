
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from pathlib import Path
import pandas as pd

from .data import load_data, load_historical_data, load_2025_data, save_upload, vegetable_names
from .forecast import make_forecast, compare_models
from .weather import get_weather

app = FastAPI(
    title="AgriSense AI API",
    version="1.0.0",
    description="Real Indian mandi data analytics and weather intelligence"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/api/health")
def health():
    d = load_data()
    return {
        "status": "ok",
        "rows": len(d),
        "data_mode": "real_csv" if len(d) else "no_data",
        "latest_date": str(d.date.max().date()) if len(d) else None,
        "date_count": int(d.date.nunique()) if len(d) else 0
    }


@app.get("/api/commodities")
def commodities():
    return vegetable_names(load_data())


@app.get("/api/filters")
def filters():
    d = load_data()
    return {
        "states": sorted(d.state.unique().tolist()),
        "markets": sorted(d.market.unique().tolist()),
        "districts": sorted(d.district.unique().tolist())
    }


@app.get("/api/prices")
def prices(
    commodity: str | None = None,
    state: str | None = None,
    market: str | None = None,
    start: str | None = None,
    end: str | None = None
):
    d = load_data()

    if commodity:
        d = d[d.commodity.str.casefold() == commodity.casefold()]

    if state and state.casefold() != "all":
        d = d[d.state.str.casefold() == state.casefold()]

    if market and market.casefold() != "all":
        d = d[d.market.str.casefold() == market.casefold()]

    if start:
        d = d[d.date >= pd.to_datetime(start)]

    if end:
        d = d[d.date <= pd.to_datetime(end)]

    latest_date = str(d.date.max().date()) if not d.empty else None

    result = d.assign(date=d.date.dt.strftime("%Y-%m-%d"))
    result = result.astype(object).where(pd.notna(result), None)

    return {
        "rows": result.to_dict(orient="records"),
        "count": len(result),
        "latest_date": latest_date
    }


@app.get("/api/summary")
def summary(commodity: str, state: str = "All", market: str = "All"):
    d = load_data()
    d = d[d.commodity.str.casefold() == commodity.casefold()]

    if state.casefold() != "all":
        d = d[d.state.str.casefold() == state.casefold()]

    if market.casefold() != "all":
        d = d[d.market.str.casefold() == market.casefold()]

    if d.empty:
        return {
            "available": False,
            "reason": "No matching real records."
        }

    latest = d.date.max()
    x = d[d.date == latest]

    return {
        "available": True,
        "date": str(latest.date()),
        "records": len(x),
        "min_price": float(x.min_price.min()),
        "max_price": float(x.max_price.max()),
        "modal_price": float(x.modal_price.mean()),
        "markets": int(x.market.nunique()),
        "states": int(x.state.nunique()),
        "arrival": float(x.arrival.sum()) if x.arrival.notna().any() else None,
        "data_rows": len(d)
    }


@app.get("/api/forecast")
def forecast(
    commodity: str,
    horizon: int = 7,
    state: str = "All",
    market: str = "All"
):
    if horizon not in [7, 15, 30]:
        raise HTTPException(400, "Horizon must be 7, 15 or 30 days.")

    return make_forecast(load_2025_data(), commodity, horizon, state, market)


@app.get("/api/model-comparison")
def model_comparison(
    commodity: str,
    state: str = "All",
    market: str = "All"
):
    return {
        "models": compare_models(load_2025_data(), commodity, state, market)
    }


@app.get("/api/weather")
def weather(place: str = "Chennai, Tamil Nadu"):
    return get_weather(place)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")

    try:
        d = save_upload(await file.read())
        return {
            "status": "uploaded",
            "rows": len(d),
            "latest_date": str(d.date.max().date()) if len(d) else None,
            "commodities": len(d.commodity.unique())
        }
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/historical-prices")
def historical_prices(
    commodity: str = "Amaranthus",
    state: str = "All",
    market: str = "All",
    district: str = "All"
):
    d = load_2025_data()

    if d.empty:
        return {
            "available": False,
            "rows": [],
            "count": 0
        }

    # Commodity filter
    d = d[
        d["commodity"].str.casefold() == commodity.casefold()
    ]
    # Market filter
    if market.casefold() != "all":
     d = d[
        d["market"].str.casefold() == market.casefold()
    ]

    # State filter only when real state data exists
    if (
        state.casefold() != "all"
        and d["state"].ne("Unknown").any()
    ):
        d = d[
            d["state"].str.casefold() == state.casefold()
        ]

    # District filter only when real district data exists
    if (
        district.casefold() != "all"
        and d["district"].ne("Unknown").any()
    ):
        d = d[
            d["district"].str.casefold() == district.casefold()
        ]

    d = d.sort_values("date")

    d = d.astype(object).where(pd.notna(d), None)

    return {
        "available": not d.empty,
        "rows": d.to_dict(orient="records"),
        "count": len(d)
    }
