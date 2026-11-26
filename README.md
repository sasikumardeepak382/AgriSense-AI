# AgriSense AI — Vegetable Market Price Forecasting & Weather Intelligence

A Windows-ready starter project with a Streamlit frontend and FastAPI backend. It bundles the real market CSV previously supplied in this workspace (`data/market_prices.csv`). Prices are source-reported Indian mandi prices in INR per quintal.

## Run on Windows

1. Install **Python 3.12** (required for the pinned dependency set) and enable “Add Python to PATH”.
2. Extract this ZIP into a normal folder, e.g. `C:\Projects\AgriSense_AI_Final`.
3. Double-click `RUN_PROJECT.bat`.
4. Wait for dependency installation and browser launch.
5. Frontend: http://localhost:8501
6. Backend Swagger docs: http://127.0.0.1:8000/docs

The batch file creates `.venv`, installs requirements, starts FastAPI and Streamlit in separate windows, and opens the frontend. Keep both windows open. First startup requires internet for Python packages and Open-Meteo weather.

## Included now

- Frontend + REST backend (FastAPI + Streamlit)
- Bundled real CSV import and CSV upload/normalization
- Latest available modal/min/max price, state/market comparisons
- Historical daily/weekly/monthly views (only as far back as the supplied data supports)
- 7/15/30-day Random Forest recursive forecast when at least 45 daily observations are available for the selected series; chronological holdout MAE/RMSE and empirical error band
- Open-Meteo geocoding, current weather, 7-day weather, cloud cover, and soil-moisture model field when returned
- Model feature importance, grounded chatbot answers, CSV exports, model comparison
- Data coverage and implementation status panel

## Important data-quality note

The bundled CSV has **16,898 rows but only one distinct observation date: 27-Oct-2026**. It includes many commodity categories, not only vegetables. The date is retained exactly as provided. It is not a live feed. With one date, multi-year history, previous-year comparison, seasonality, daily change, and price forecasting are not statistically supportable. Forecast endpoints return `available: false` rather than fabricate predictions. Upload a multi-year AGMARKNET/data.gov.in CSV to unlock those analyses.

The CSV contains the following source fields: State, District, Market, Commodity, Variety, Grade, Arrival_Date, Min Price, Max Price, Modal Price. The bundled file does not contain an arrival quantity field, so arrivals/supply analysis remains unavailable until a verified arrivals dataset is supplied.

## Data upload

In the app, open **Data & Model Lab → Upload verified AGMARKNET / data.gov.in CSV**. Common column aliases are recognized, including `Arrival_Date`, `Min_x0020_Price`, `Max_x0020_Price`, `Modal_x0020_Price`. The uploaded CSV replaces `data/market_prices.csv`; keep a backup first if you need the original.

## APIs

- `GET /api/health`
- `GET /api/commodities`
- `GET /api/filters`
- `GET /api/prices?commodity=Tomato`
- `GET /api/summary?commodity=Tomato`
- `GET /api/forecast?commodity=Tomato&horizon=7` (horizon: 7, 15, 30)
- `GET /api/weather?place=Chennai,Tamil Nadu`
- `POST /api/upload` (multipart CSV file)
- `GET /api/model-comparison?commodity=Tomato`

## Honest implementation roadmap

Not represented as completed in this ZIP: data.gov.in scheduled API ingestion (the previously attempted endpoint returned 403), long-range historical weather, weather-price causal attribution, diesel/fuel and transport feeds, crop production/cultivated-area data, festival calendar, import/export/policy feeds, SHAP, XGBoost, LightGBM, SARIMA, LSTM, Temporal Fusion Transformer, calibrated prediction intervals, RAG/LLM chatbot, authentication, personalized watchlists, notifications, automated daily jobs, PDF reports, state map, crop supply/harvest/demand forecasting, model drift monitoring. These need verified data providers, API credentials where applicable, and additional implementation/testing.

## Notes

- No synthetic price data is generated or mixed with the real CSV.
- Open-Meteo weather is a public model/API source; soil moisture is model-derived when available, not a sensor observation.
- Model feature importance is predictive association, not proof of causal impact.
- Forecasts are estimates, not guaranteed market prices.
