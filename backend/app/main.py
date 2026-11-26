
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from pathlib import Path
import pandas as pd
import asyncio

from .data import load_data, load_historical_data, load_2025_data, save_upload, vegetable_names
from .forecast import make_forecast, compare_models, explain_model
from .weather import get_weather
from .chatbot import ask_agrisense
from .database import Base, engine, SessionLocal
from .auth_routes import router as auth_router, require_user
from .watchlist_routes import router as watchlist_router
from .alert_routes import router as alert_router
from .report_routes import router as report_router

app = FastAPI(
    title="AgriSense AI API",
    version="1.0.0",
    description="Real Indian mandi data analytics and weather intelligence"
)
Base.metadata.create_all(bind=engine)
async def monitor_price_alerts():
    while True:
        try:
            db = SessionLocal()
            try:
                from .models import PriceAlert
                from .data import load_data

                df = load_data()

                if not df.empty:
                    df["modal_price"] = pd.to_numeric(
                        df["modal_price"], errors="coerce"
                    )

                    latest_date = df["date"].max()
                    latest = df[df["date"] == latest_date]

                    alerts = db.query(PriceAlert).filter(
                        PriceAlert.is_active == 1
                    ).all()

                    for alert in alerts:
                        matched = latest[
                            latest["commodity"].str.casefold()
                            == alert.commodity.casefold()
                        ]["modal_price"].dropna()

                        if not matched.empty:
                            current_price = float(matched.mean())

                            alert.last_checked_price = int(current_price)

                            if alert.condition == "above":
                                alert.is_triggered = int(
                                    current_price >= alert.target_price
                                )
                            else:
                                alert.is_triggered = int(
                                    current_price <= alert.target_price
                                )

                    db.commit()
            finally:
                db.close()

        except Exception as e:
            print("Price alert monitor error:", e)

        await asyncio.sleep(300)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(alert_router)
app.include_router(report_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def start_alert_monitor():
    app.state.alert_monitor_task = asyncio.create_task(
        monitor_price_alerts()
    )


@app.on_event("shutdown")
async def stop_alert_monitor():
    app.state.alert_monitor_task.cancel()


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
def commodities(user=Depends(require_user)):
    return vegetable_names(load_data())


@app.get("/api/filters")
def filters(user=Depends(require_user)):
    d = load_data()
    return {
        "states": sorted(d.state.unique().tolist()),
        "markets": sorted(d.market.unique().tolist()),
        "districts": sorted(d.district.unique().tolist())
    }


@app.get("/api/prices")
def prices(
    user=Depends(require_user),
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
def summary(
    commodity: str,
    user=Depends(require_user),
    state: str = "All",
    market: str = "All"
):
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
    user=Depends(require_user),
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
    user=Depends(require_user),
    state: str = "All",
    market: str = "All"
):
    return {
        "models": compare_models(load_2025_data(), commodity, state, market)
    }


@app.get("/api/weather")
def weather(
    user=Depends(require_user),
    place: str = "Chennai, Tamil Nadu"
):
    return get_weather(place)


@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    user=Depends(require_user)
):
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
        user=Depends(require_user),
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
@app.get("/api/explainability")
def explainability(
    commodity: str,
    user=Depends(require_user),
    state: str = "All",
    market: str = "All"
):
    d = load_2025_data()
    return explain_model(d, commodity, state, market)
def chat(payload: dict):
    question = str(payload.get("question", "")).strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    return ask_agrisense(
        question=question,
        commodity=payload.get("commodity"),
        state=payload.get("state", "All"),
        market=payload.get("market", "All")
    )