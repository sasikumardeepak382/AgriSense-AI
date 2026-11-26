import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from backend.app.data import load_data
from sklearn.ensemble import RandomForestRegressor

API = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AgriSense AI",
    page_icon="🌱",
    layout="wide"
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8fafc;
        color: #263238;
    }

    .block-container {
        padding-top: 1.5rem;
    }

    [data-testid="stSidebar"] {
        background-color: #f1f5f2;
    }

    h1, h2, h3 {
        color: #17452d !important;
    }

    p, label, span {
        color: #263238;
        font-size: 16px;
    }

    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
    }

    [data-testid="stMetricLabel"] {
        font-size: 16px !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 26px !important;
        color: #17452d !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# -----------------------------
# API FUNCTIONS
# -----------------------------


def api(path, params=None):
    try:
        headers = {}

        token = st.session_state.get("access_token")

        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(
            API + path,
            params=params,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        return response.json()

    except Exception as exc:
        return {"error": str(exc)}


def money(value):
    if value is None or pd.isna(value):
        return "—"
    return f"₹{value:,.0f}"


def getdf(params):
    result = api("/api/prices", params)

    if result.get("error"):
        return pd.DataFrame()

    data = pd.DataFrame(result.get("rows", []))

    if not data.empty and "date" in data.columns:
        data["date"] = pd.to_datetime(
            data["date"],
            errors="coerce"
        )

    return data


# -----------------------------
# HEADER
# -----------------------------

st.title("🌱 AgriSense AI")

st.caption(
    "Vegetable Market Price Forecasting & Weather Intelligence "
    "| PAST • CURRENT • FUTURE"
)

health = api("/api/health")
# INITIALIZE LOGIN SESSION
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user" not in st.session_state:
    st.session_state.user = None

if health.get("error"):
    st.error(
        "Backend is not running. "
        "Please start the backend and refresh this page."
    )
    st.stop()

 
# -----------------------------
# LOGIN / SIGNUP
# -----------------------------

if not st.session_state.access_token:

    st.title("AgriSense AI")
    st.subheader("Welcome")

    auth_mode = st.radio(
        "Choose an option",
        ["Login", "Signup"],
        horizontal=True
    )

    if auth_mode == "Login":

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            try:
                response = requests.post(
                    f"{API}/api/auth/login",
                    json={
                        "email": email,
                        "password": password
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    result = response.json()
                    st.session_state.access_token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Login failed"))

            except requests.RequestException:
                st.error("Unable to connect to backend.")

    else:

        name = st.text_input("Name")
        email = st.text_input("Email address")
        password = st.text_input("Create password", type="password")

        if st.button("Create Account"):
            try:
                response = requests.post(
                    f"{API}/api/auth/signup",
                    json={
                        "name": name,
                        "email": email,
                        "password": password
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    result = response.json()
                    st.session_state.access_token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.success("Account created successfully!")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Signup failed"))

            except requests.RequestException:
                st.error("Unable to connect to backend.")

    st.stop()
   


# -----------------------------
# SIDEBAR
# -----------------------------

# AUTH SESSION
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("Control Center")
    if st.session_state.user:
        st.write(f"Welcome, {st.session_state.user['name']}")

        if st.button("Logout"):
            st.session_state.access_token = None
            st.session_state.user = None
            st.rerun()

    page = st.radio(
        "Navigate",
        [
            "Market Overview",
            "Historical Analysis",
            "Future Forecast",
            "Weather Intelligence",
            "AI Price Insights",
            "AI Chatbot",
            "Data & Model Lab",
            "Watchlist",
            "Price Alerts",
            "PDF Reports",
            "Maps",
            "Supply Forecasting", 

        ]
    )


commodities = api("/api/commodities")
commodities = commodities if isinstance(commodities, list) else []

vegetable_terms = [
        "tomato", "onion", "potato", "brinjal",
        "eggplant", "bhindi", "ladies finger",
        "okra", "chilli", "pepper", "cauliflower",
        "cabbage", "bottle gourd", "bitter gourd",
        "pumpkin", "cucumber", "raddish", "radish",
        "carrot", "ridgeguard", "ridge gourd",
        "drumstick", "beetroot", "amaranthus",
        "cluster beans", "beans", "capsicum",
        "ashgourd", "snakeguard", "chow chow",
        "colacasia", "yam", "garlic", "ginger",
        "coriander", "mint", "spinach", "peas",
        "mushroom", "turnip", "sweet potato",
        "fenugreek", "lemon", "raw banana",
        "banana - green"
    ]

commodities = [
        item for item in commodities
        if isinstance(item, str)
        and any(term in item.casefold() for term in vegetable_terms)
    ]

if not commodities:
        st.warning(
            "No vegetable records found in the loaded real data."
        )

vegetable = st.selectbox(
        "Vegetable / Commodity",
        commodities or ["Tomato"]
    )

filters = api("/api/filters")
if not isinstance(filters, dict):
        filters = {}

states = filters.get("states", [])
markets = filters.get("markets", [])

state = st.selectbox(
        "State",
        ["All"] + states
    )

market = st.selectbox(
        "Market",
        ["All"] + markets
    )

st.caption(
        "All prices are source prices in ₹ per quintal."
    )

st.divider()

st.caption(
        f"Dataset rows: {health.get('rows', 0):,} "
        f"| Latest source date: "
        f"{health.get('latest_date') or 'N/A'}"
    )

# AUTHENTICATION CHECK
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user" not in st.session_state:
    st.session_state.user = None
if not st.session_state.access_token:
    st.title("AgriSense AI - Login")
    st.info("Please login to access the dashboard.")
    st.stop()
params = {
    "commodity": vegetable,
    "state": state,
    "market": market
}

df = getdf(params)
summary = api("/api/summary", params)


# ==================================================
# 1. MARKET OVERVIEW
# ==================================================

if page == "Market Overview":

    st.subheader("Current market snapshot")

    if summary.get("available"):

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Average modal price",
            money(summary.get("modal_price"))
        )

        col2.metric(
            "Minimum",
            money(summary.get("min_price"))
        )

        col3.metric(
            "Maximum",
            money(summary.get("max_price"))
        )

        col4.metric(
            "Markets",
            summary.get("markets", 0)
        )

        st.caption(
            f"Latest available date: {summary.get('date', 'N/A')} "
            f"· {summary.get('records', 0)} matching records"
        )

        required_columns = [
            "date", "commodity", "state",
            "district", "market", "min_price",
            "max_price", "modal_price", "arrival"
        ]

        missing_columns = [
            column for column in required_columns
            if column not in df.columns
        ]

        if df.empty:

            st.warning(
                "The summary endpoint found matching records, "
                "but the prices endpoint returned no rows."
            )

        elif missing_columns:

            st.error(
                "Price data response is missing expected columns: "
                + ", ".join(missing_columns)
            )

            st.caption(
                "Columns received: "
                + ", ".join(map(str, df.columns))
            )

        else:

            st.dataframe(
                df.sort_values("modal_price")[required_columns],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("#### State comparison")

            state_comparison = (
                df.groupby("state", as_index=False)["modal_price"]
                .mean()
                .sort_values("modal_price")
            )

            st.plotly_chart(
                px.bar(
                    state_comparison,
                    x="state",
                    y="modal_price",
                    title="Average modal price by state"
                ),
                use_container_width=True
            )

    else:
        st.info(
            summary.get("reason", "No matching data")
        )

    st.warning(
        "The bundled real CSV currently contains records "
        "for 27-Oct-2026 only. The source date is shown as-is; "
        "it is not described as live/today data."
    )

    st.markdown("#### Data coverage")

    st.write(
        f"{health.get('rows', 0):,} real CSV rows "
        f"· {health.get('date_count', 0)} distinct date(s) "
        f"· {len(commodities):,} commodities"
    )


# ==================================================
# 2. HISTORICAL ANALYSIS
# ==================================================

elif page == "Historical Analysis":

    st.subheader("Historical price analysis")
    st.markdown("### 📅 Monthly historical market prices")

    historical_result = api("/api/historical-prices")

    if historical_result.get("available"):

        historical_df = pd.DataFrame(
            historical_result.get("rows", [])
        )

        if not historical_df.empty:

            # Convert date column
            if "date" not in historical_df.columns:
                st.error(
                    "The historical response does not contain a date column."
                )
                st.stop()

            historical_df["date"] = pd.to_datetime(
                historical_df["date"],
                errors="coerce"
            )

            # Accept either modal_price or average_price from the API.
            if "modal_price" in historical_df.columns:
                historical_df["price"] = pd.to_numeric(
                    historical_df["modal_price"],
                    errors="coerce"
                )
            elif "average_price" in historical_df.columns:
                historical_df["price"] = pd.to_numeric(
                    historical_df["average_price"],
                    errors="coerce"
                )
            else:
                st.error(
                    "Historical price column not found. "
                    "Expected modal_price or average_price."
                )
                st.stop()

            historical_df = historical_df.dropna(
                subset=["date", "price"]
            )

            # Commodity filter
            if "commodity" in historical_df.columns:
                historical_df = historical_df[
                    historical_df["commodity"].astype(str).str.casefold()
                    == vegetable.casefold()
                ]

            # State filter
            if state != "All" and "state" in historical_df.columns:
                historical_df = historical_df[
                    historical_df["state"].astype(str).str.casefold()
                    == state.casefold()
                ]

            # Market filter
            if market != "All" and "market" in historical_df.columns:
                historical_df = historical_df[
                    historical_df["market"].astype(str).str.casefold()
                    == market.casefold()
                ]

            # District filter
            if "district" in historical_df.columns:
                district_options = sorted(
                    historical_df["district"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                selected_district = st.selectbox(
                    "Historical District",
                    ["All"] + district_options,
                    key="historical_district"
                )

                if selected_district != "All":
                    historical_df = historical_df[
                        historical_df["district"].astype(str).str.casefold()
                        == selected_district.casefold()
                    ]
            else:
                st.info(
                    "District information is not available "
                    "in this historical dataset."
                )

            if not historical_df.empty:

                # Monthly aggregation
                historical_df["month"] = (
                    historical_df["date"]
                    .dt.to_period("M")
                    .dt.to_timestamp()
                )

                monthly = (
                    historical_df.groupby("month", as_index=False)["price"]
                    .mean()
                )

                st.caption(
                    f"Source: AGMARKNET historical data "
                    f"| Commodity: {vegetable}"
                )

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Historical records",
                    len(historical_df)
                )

                col2.metric(
                    "Markets covered",
                    historical_df["market"].nunique()
                    if "market" in historical_df.columns else 0
                )

                col3.metric(
                    "Months covered",
                    len(monthly)
                )

                st.markdown("#### Monthly price trend")

                st.plotly_chart(
                    px.line(
                        monthly,
                        x="month",
                        y="price",
                        markers=True,
                        title="Monthly average modal price (₹/quintal)"
                    ),
                    use_container_width=True
                )

                # Top 10 market comparison
                if "market" in historical_df.columns:

                    st.markdown(
                        "#### Top 10 market price comparison"
                    )

                    market_comparison = (
                        historical_df.groupby(
                            "market", as_index=False
                        )["price"]
                        .mean()
                        .nlargest(10, "price")
                        .sort_values("price")
                    )

                    st.plotly_chart(
                        px.bar(
                            market_comparison,
                            x="market",
                            y="price",
                            title="Top 10 Markets by Average Price"
                        ),
                        use_container_width=True
                    )

                # Historical data table
                st.markdown("#### Historical data table")

                display_columns = [
                    "date", "state", "district",
                    "market", "commodity", "year",
                    "month", "price"
                ]

                display_columns = [
                    column for column in display_columns
                    if column in historical_df.columns
                ]

                display_history = (
                    historical_df[display_columns]
                    .sort_values("date")
                )

                display_history = display_history.rename(
                    columns={
                        "price": "Average Modal Price (₹/quintal)"
                    }
                )

                st.dataframe(
                    display_history,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "Download historical CSV",
                    historical_df.to_csv(index=False),
                    "agrisense_monthly_history.csv",
                    "text/csv"
                )

            else:
                st.info(
                    "No historical records match the selected filters."
                )

        else:
            st.info("Historical CSV contains no records.")

    else:
        st.warning(
            "Monthly historical data is not available from the backend."
        )

    # Daily / weekly historical analysis
    st.divider()
    st.markdown("### Daily / weekly historical analysis")

    if df.empty:

        st.info(
            "No matching daily records available in the current dataset."
        )

    elif "date" not in df.columns or "modal_price" not in df.columns:

        st.warning(
            "Daily data must contain date and modal_price columns."
        )

    else:

        frequency = st.selectbox(
            "Time aggregation",
            ["Daily", "Weekly", "Monthly"]
        )

        resample_rule = {
            "Daily": "D",
            "Weekly": "W",
            "Monthly": "MS"
        }[frequency]

        daily_df = historical_df.copy()

        daily_df["date"] = pd.to_datetime(
            daily_df["date"],
            errors="coerce"
        )

        daily_df["modal_price"] = pd.to_numeric(
            daily_df["modal_price"],
            errors="coerce"
        )

        daily_df = daily_df.dropna(
            subset=["date", "modal_price"]
        )

        time_series = (
            daily_df.set_index("date")["modal_price"]
            .resample(resample_rule)
            .mean()
            .dropna()
            .reset_index()
        )

        if len(time_series) < 2:
            st.warning(
                f"Not enough historical dates for {frequency} trend. "
                "Please upload more real daily price records."
            )
        else:
            st.plotly_chart(
                px.line(
                    time_series,
                    x="date",
                    y="modal_price",
                    markers=True,
                    title=f"{vegetable} {frequency} modal price"
                ),
                use_container_width=True
            )

        if not time_series.empty:

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Minimum",
                money(float(time_series["modal_price"].min()))
            )

            col2.metric(
                "Maximum",
                money(float(time_series["modal_price"].max()))
            )

            col3.metric(
                "Modal average",
                money(float(time_series["modal_price"].mean()))
            )

        st.markdown("#### Daily market comparison")

        if "market" in daily_df.columns:

            daily_comparison = (
                daily_df.groupby("market", as_index=False)["modal_price"]
                .mean()
                .nlargest(10, "modal_price")
                .sort_values("modal_price")
            )

            st.plotly_chart(
                px.bar(
                    daily_comparison,
                    x="market",
                    y="modal_price",
                    title="Top 10 Daily Markets by Average Modal Price"
                ),
                use_container_width=True
            )

        st.info(
            "Year-over-year and seasonal trends require "
            "multiple years of dated observations."
        )

        st.download_button(
            "Download filtered daily history CSV",
            daily_df.to_csv(index=False),
            "agrisense_history.csv",
            "text/csv"
        )


# ==================================================
# 3. FUTURE FORECAST
# ==================================================

elif page == "Future Forecast":

    st.subheader("🔮 Vegetable price forecasting")

    st.write(
        "Generate a 7, 15 or 30-day price forecast "
        "using the available real historical market data."
    )

    st.caption(
        "Forecast availability depends on sufficient "
        "historical observations."
    )

    horizon = st.radio(
        "Forecast horizon",
        [7, 15, 30],
        horizontal=True
    )

    if st.button("Generate forecast", type="primary"):

        with st.spinner("Training chronological baseline model..."):

            st.session_state["fc"] = api(
                "/api/forecast",
                {
                    **params,
                    "horizon": horizon
                }
            )

    forecast_result = st.session_state.get("fc")

    if forecast_result:

        if not forecast_result.get("available"):

            st.warning(
                forecast_result.get(
                    "reason",
                    "Forecast unavailable"
                )
            )

        else:

            forecast_rows = forecast_result.get("forecast", [])

            if not forecast_rows:
                st.warning("The forecast endpoint returned no forecast rows.")
            else:

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Last forecast price",
                    money(
                        forecast_rows[-1].get("predicted_modal_price")
                    )
                )

                col2.metric(
                    "Expected change",
                    f"{forecast_result.get('change_pct', 0):+.2f}%"
                )

                col3.metric(
                    "Holdout MAE",
                    money(forecast_result.get("mae"))
                )

                forecast_df = pd.DataFrame(forecast_rows)

                st.markdown("#### Forecast price trend")

                forecast_columns = [
                    column for column in [
                        "predicted_modal_price",
                        "lower_estimate",
                        "upper_estimate"
                    ]
                    if column in forecast_df.columns
                ]

                st.plotly_chart(
                    px.line(
                        forecast_df,
                        x="date",
                        y=forecast_columns,
                        title="Forecast and empirical error band"
                    ),
                    use_container_width=True
                )

                st.markdown("#### Forecast data")

                st.dataframe(
                    forecast_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    f"Model: {forecast_result.get('model', 'N/A')} "
                    f"· RMSE: ₹{forecast_result.get('rmse', 0):,.2f} "
                    f"· {forecast_result.get('confidence_note', '')}"
                )

                st.download_button(
                    "Download forecast CSV",
                    forecast_df.to_csv(index=False),
                    "agrisense_forecast.csv",
                    "text/csv"
                )

    else:
        st.info(
            "Choose a horizon and click Generate forecast. "
            "Forecasts are disabled when the selected "
            "real series is too short."
        )


# ==================================================
# 4. WEATHER INTELLIGENCE
# ==================================================

elif page == "Weather Intelligence":

    st.subheader("🌦️ Weather intelligence")

    place = st.text_input(
        "Location",
        "Chennai, Tamil Nadu"
    )

    if st.button(
        "Fetch current weather + 7-day forecast",
        type="primary"
    ):

        st.session_state["weather"] = api(
            "/api/weather",
            {"place": place}
        )

    weather_result = st.session_state.get("weather")

    if weather_result:

        if not weather_result.get("available"):

            st.error(
                weather_result.get(
                    "error",
                    "Weather data unavailable"
                )
            )

        else:

            current_weather = weather_result.get("current", {})

            st.caption(
                f"{weather_result.get('location', place)} "
                f"· Source: {weather_result.get('source', 'N/A')}"
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Temperature",
                f"{current_weather.get('temperature_2m', '—')} °C"
            )

            col2.metric(
                "Humidity",
                f"{current_weather.get('relative_humidity_2m', '—')}%"
            )

            col3.metric(
                "Rain",
                f"{current_weather.get('precipitation', '—')} mm"
            )

            col4.metric(
                "Wind",
                f"{current_weather.get('wind_speed_10m', '—')} km/h"
            )

            st.metric(
                "Cloud cover",
                f"{current_weather.get('cloud_cover', '—')}%"
            )

            if weather_result.get("soil_moisture_latest") is not None:
                st.metric(
                    "Soil moisture (0–7 cm)",
                    weather_result["soil_moisture_latest"]
                )

            daily_weather = pd.DataFrame(
                weather_result.get("daily", [])
            )

            if not daily_weather.empty:

                if {"date", "temp_max", "temp_min"}.issubset(
                    daily_weather.columns
                ):
                    st.plotly_chart(
                        px.line(
                            daily_weather,
                            x="date",
                            y=["temp_max", "temp_min"],
                            title="7-day temperature outlook"
                        ),
                        use_container_width=True
                    )

                if {"date", "rain_sum"}.issubset(
                    daily_weather.columns
                ):
                    st.plotly_chart(
                        px.bar(
                            daily_weather,
                            x="date",
                            y="rain_sum",
                            title="7-day rainfall (mm)"
                        ),
                        use_container_width=True
                    )

            st.caption(
                weather_result.get("note", "")
                + " Historical weather and official alerts "
                + "require additional provider integration."
            )

    else:
        st.info(
            "Click the button to retrieve current conditions and forecast."
        )


# ==================================================
# 5. AI PRICE INSIGHTS
# ==================================================

elif page == "AI Price Insights":

    st.subheader("🤖 AI-assisted price movement analysis")

    if df.empty:

        st.info(
            "Load real market records to enable price insights."
        )

    elif "date" not in df.columns or "modal_price" not in df.columns:

        st.warning(
            "Price insights require date and modal_price columns."
        )

    else:

        

        historical_result = api(
            "/api/historical-prices",
            params
        )

        insights_df = pd.DataFrame(
            historical_result.get("rows", [])
        )

        if not insights_df.empty:
            insights_df["date"] = pd.to_datetime(
                insights_df["date"],
                errors="coerce"
            )

            insights_df["modal_price"] = pd.to_numeric(
                insights_df["modal_price"],
                errors="coerce"
            )

            daily_prices = (
                insights_df.dropna(
                    subset=["date", "modal_price"]
                )
                .groupby("date")["modal_price"]
                .mean()
                .sort_index()
            )
        else:
            daily_prices = pd.Series(dtype=float)



        if len(daily_prices) >= 2:

            previous_price = daily_prices.iloc[-2]
            latest_price = daily_prices.iloc[-1]

            change_percent = (
                (latest_price - previous_price) / previous_price * 100
                if previous_price else 0
            )

            st.write(
                f"Latest available observed modal price moved "
                f"{change_percent:+.2f}% versus the previous available "
                f"date in the filtered records."
            )

        else:
            st.info(
                "Only one date is present; a daily price "
                "change cannot be calculated."
            )

        forecast_result = api(
            "/api/forecast",
            {
                **params,
                "horizon": 7
            }
        )

        if forecast_result.get("available"):

            st.write(
                f"The Random Forest baseline estimates "
                f"{forecast_result.get('change_pct', 0):+.2f}% over 7 days. "
                f"Chronological holdout MAE: "
                f"₹{forecast_result.get('mae', 0):,.2f}."
            )

            feature_importance = pd.DataFrame(
                forecast_result.get("feature_importance", [])
            )

            if not feature_importance.empty and {
                "importance", "feature"
            }.issubset(feature_importance.columns):

                st.plotly_chart(
                    px.bar(
                        feature_importance,
                        x="importance",
                        y="feature",
                        orientation="h",
                        title="Model feature importance (not causal impact)"
                    ),
                    use_container_width=True
                )

        else:
            st.warning(
                forecast_result.get(
                    "reason",
                    "Forecast unavailable"
                )
            )

        # SHAP Explainability
        shap_result = api(
            "/api/explainability",
            params
        )

        if shap_result.get("available"):
            st.subheader("SHAP Model Explainability")

            shap_df = pd.DataFrame(
                shap_result.get("top_features", [])
            )
            st.write("SHAP data:", shap_df)
            if not shap_df.empty:
                st.plotly_chart(
                    px.bar(
                        shap_df,
                        x="mean_shap_value",
                        y="feature",
                        orientation="h",
                        title="Top SHAP Feature Contributions"
                    ),
                    use_container_width=True
                )

        else:
            st.info(
                shap_result.get(
                    "reason",
                    "SHAP explanation unavailable"
                )
            )


        st.info(
            "Weather, fuel, transport, festivals, cultivated area, "
            "production, storage, trade and policy are not yet joined "
            "as verified explanatory datasets. The system will not "
            "invent a cause or claim causation from price-only data."
        )



# ==================================================
# 6. AI CHATBOT
# ==================================================

elif page == "AI Chatbot":

    st.subheader("💬 AgriSense AI Market Assistant")

    st.caption(
        "RAG-powered answers using real market CSV data "
        "with Gemini AI."
    )

    question = st.chat_input(
        "Ask about vegetable prices, markets or trends..."
    )

    if question:

        st.chat_message("user").write(question)

        question_lower = question.casefold()

        requested_vegetable = next(
            (
                item for item in commodities
                if item.casefold() in question_lower
            ),
            vegetable
        )

        payload = {
            "question": question,
            "commodity": requested_vegetable,
            "state": params.get("state", "All"),
            "market": params.get("market", "All")
        }

        with st.chat_message("assistant"):

            with st.spinner("AgriSense AI is analysing real market data..."):

                try:
                    response = requests.post(
                        API + "/api/chat",
                        json=payload,
                        timeout=90
                    )

                    response.raise_for_status()
                    result = response.json()

                    st.markdown(result.get(
                        "answer",
                        "No answer received."
                    ))

                    st.caption(
                        f"AI Model: {result.get('model', 'N/A')} "
                        f"| Data date: {result.get('retrieved_date', 'N/A')}"
                    )

                    sources = result.get("sources", [])

                    if sources:
                        with st.expander("View retrieved real market records"):
                            st.dataframe(
                                pd.DataFrame(sources),
                                use_container_width=True
                            )

                except Exception as exc:
                    st.error(f"Chatbot error: {exc}")


# ==================================================
# 7. DATA & MODEL LAB
# ==================================================


elif page == "Data & Model Lab":

    st.subheader("🧪 Data management and model lab")

    st.write(
        "Current source coverage",
        health
    )

    st.markdown(
        "**Upload verified AGMARKNET / data.gov.in CSV**"
    )

    uploaded_file = st.file_uploader(
        "Choose CSV",
        type=["csv"]
    )

    if uploaded_file and st.button(
        "Import CSV to backend",
        type="primary"
    ):

        try:

            response = requests.post(
                API + "/api/upload",
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "text/csv"
                    )
                },
                timeout=90
            )

            response.raise_for_status()

            st.success(response.json())
            st.cache_data.clear()

        except Exception as exc:

            st.error(str(exc))

    
    st.markdown("### ML Model Performance Comparison")

    if st.button("Compare baseline models", type="primary"):

        comparison_result = api(
            "/api/model-comparison",
            params
        )

        models = comparison_result.get("models", [])

        if models:

            comparison_df = pd.DataFrame(models)

            best_model = comparison_df.iloc[0]

            st.success(
                f"Best Model: {best_model['model']} "
                f"| MAE: ₹{best_model['mae']}"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Best Model",
                best_model["model"]
            )

            col2.metric(
                "MAE",
                f"₹{best_model['mae']}"
            )

            col3.metric(
                "RMSE",
                f"₹{best_model['rmse']}"
            )

            st.markdown("#### Complete Model Results")

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("#### MAE Comparison")

            st.bar_chart(
                comparison_df.set_index("model")["mae"]
            )

            st.markdown("#### RMSE Comparison")

            st.bar_chart(
                comparison_df.set_index("model")["rmse"]
            )

            if "r2_score" in comparison_df.columns:

                st.markdown("#### R² Score Comparison")

                st.bar_chart(
                    comparison_df.set_index("model")["r2_score"]
                )

        else:

            st.info(
                "At least 50 engineered daily observations "
                "are required for chronological model comparison."
            )

    st.markdown("**Feature implementation status**")

    feature_status =[
        ("Real market CSV import", "Available"),
        (
            "Daily / weekly / monthly analysis",
            "Available when history exists"
        ),
        (
            "7 / 15 / 30-day forecast",
            "Conditional on sufficient history"
        ),
        (
            "Weather current + 7-day",
            "Open-Meteo integration"
        ),
        (
            "Soil moisture",
            "Open-Meteo model field when returned"
        ),
        (
            "SHAP explainability",
            "Implemented — Random Forest + SHAP"
        ),
        (
    "XGBoost / LightGBM / SARIMA",
    "Implemented — Model Comparison"
),
(
    "LSTM",
    "Implemented — Model Comparison"
),
(
    "TFT",
"Implemented — Model Comparison"
),
               (
            "RAG LLM chatbot",
            "Implemented - Gemini + RAG"
        ),
        (
            "Authentication",
            "Implemented - Login / Signup / Logout"
        ),
        (
            "Watchlists",
            "Implemented — Add / View / Remove"
        ),
        (
            "Automated alerts",
            "Implemented"
        ),
        (
            "PDF reports / maps / supply forecasting",
            "Implemented - Tested"
        )
          ]

    st.dataframe(
        pd.DataFrame(
            feature_status,
            columns=["Feature", "Status"]
        ),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Do not treat unimplemented items as completed "
        "project capabilities. See README for next-stage roadmap."
    )

elif page == "Watchlist":

    st.title("My Watchlist")
    st.caption("Save and track your favourite vegetables.")

    commodity = st.text_input(
        "Enter vegetable name",
        placeholder="Example: Tomato"
    )

    if st.button("Add to Watchlist"):

        if commodity.strip():

            try:
                response = requests.post(
                    f"{API}/api/watchlist/",
                    json={"commodity": commodity},
                    headers={
                        "Authorization": (
                            f"Bearer {st.session_state.access_token}"
                        )
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    st.success("Added to your watchlist!")
                    st.rerun()
                else:
                    st.error(
                        response.json().get(
                            "detail", "Unable to add vegetable"
                        )
                    )

            except requests.RequestException:
                st.error("Backend connection failed.")

elif page == "Maps":

    st.title("🗺️ Agricultural Market Map")
    st.caption("Explore market locations by state and district.")

    df_map = load_data()

    locations = df_map[
        (df_map["state"] != "Unknown") &
        (df_map["district"] != "Unknown")
    ].copy()

    states = sorted(locations["state"].dropna().unique())

    if not states:
        st.warning("No valid state locations found.")

    else:
        selected_state = st.selectbox(
            "Select State",
            states
        )

        state_data = locations[
            locations["state"] == selected_state
        ]


        districts = sorted(
            state_data["district"].dropna().unique()
        )

        selected_district = st.selectbox(
            "Select District",
            districts
        )

        if st.button("Show District on Map"):

            try:
                geolocator = Nominatim(
                    user_agent="AgriSenseAI_MarketMap"
                )

                location = geolocator.geocode(
                    f"{selected_district}, {selected_state}, India",
                    timeout=15
                )

                if location:
                    market_map = folium.Map(
                        location=[
                            location.latitude,
                            location.longitude
                        ],
                        zoom_start=10
                    )

                    folium.Marker(
                        [
                            location.latitude,
                            location.longitude
                        ],
                        popup=f"{selected_district}, {selected_state}",
                        tooltip="District Location"
                    ).add_to(market_map)

                    st_folium(
                        market_map,
                        width=900,
                        height=550
                    )

                else:
                    st.warning("Location coordinates not found.")

            except Exception as e:
                st.error(f"Map error: {e}")
                
elif page == "Supply Forecasting":

    st.title("📦 Supply Forecasting")
    st.caption("Analyze historical vegetable arrivals and supply trends.")

    df_supply = load_data()

    if df_supply.empty:
        st.warning("No real market data available.")

    else:
        commodities = sorted(
            df_supply["commodity"].dropna().unique()
        )

        selected_commodity = st.selectbox(
            "Select Commodity",
            commodities,
            key="supply_commodity"
        )

        supply_data = df_supply[
            df_supply["commodity"] == selected_commodity
        ].copy()

        supply_data["date"] = pd.to_datetime(
            supply_data["date"], errors="coerce"
        )

        supply_data["arrival"] = pd.to_numeric(
            supply_data["arrival"], errors="coerce"
        )

        supply_data = supply_data.dropna(
            subset=["date", "arrival"]
        )

        if supply_data.empty:
            st.warning("No arrival data available for this commodity.")

        else:
            daily_supply = (
                supply_data.groupby("date")["arrival"]
                .sum()
                .sort_index()
            )
            daily_supply = daily_supply.asfreq("D")
            daily_supply = daily_supply.interpolate(method="time")

            st.metric(
                "Total Recorded Arrivals",
                f"{daily_supply.sum():,.2f}"
            )

            st.line_chart(daily_supply)
            st.subheader("🤖 7-Day Supply Forecast")

            feature_data = pd.DataFrame({
                "arrival": daily_supply
            })

            feature_data["lag_1"] = feature_data["arrival"].shift(1)
            feature_data["lag_2"] = feature_data["arrival"].shift(2)
            feature_data["lag_3"] = feature_data["arrival"].shift(3)
            feature_data["lag_7"] = feature_data["arrival"].shift(7)
            feature_data["lag_14"] = feature_data["arrival"].shift(14)

            feature_data["rolling_7"] = (
                feature_data["arrival"].shift(1).rolling(7).mean()
            )

            feature_data["rolling_14"] = (
                feature_data["arrival"].shift(1).rolling(14).mean()
            )

            feature_data["dayofweek"] = feature_data.index.dayofweek
            feature_data["month"] = feature_data.index.month
            feature_data["dayofyear"] = feature_data.index.dayofyear

            feature_data = feature_data.dropna()
            feature_columns = [
                "lag_1",
                "lag_2",
                "lag_3",
                "lag_7",
                "lag_14",
                "rolling_7",
                "rolling_14",
                "dayofweek",
                "month",
                "dayofyear"
            ]

            split_index = int(len(feature_data) * 0.8)

            X_train = feature_data[feature_columns].iloc[:split_index]
            y_train = feature_data["arrival"].iloc[:split_index]

            X_test = feature_data[feature_columns].iloc[split_index:]
            y_test = feature_data["arrival"].iloc[split_index:]

            test_model = RandomForestRegressor(
                n_estimators=200,
                random_state=42,
                min_samples_leaf=2,
                n_jobs=-1
            )

            test_model.fit(X_train, y_train)

            predictions = test_model.predict(X_test)

            mae = (y_test - predictions).abs().mean()

            st.metric("Validation MAE", f"{mae:,.2f}")
            final_model = RandomForestRegressor(
                n_estimators=200,
                random_state=42,
                min_samples_leaf=2,
                n_jobs=-1
            )

            final_model.fit(
                feature_data[feature_columns],
                feature_data["arrival"]
            )

            history = daily_supply.copy()
            future_results = []

            for i in range(7):
                next_date = history.index[-1] + pd.Timedelta(days=1)

                next_features = pd.DataFrame([{
                    "lag_1": history.iloc[-1],
                    "lag_2": history.iloc[-2],
                    "lag_3": history.iloc[-3],
                    "lag_7": history.iloc[-7],
                    "lag_14": history.iloc[-14],
                    "rolling_7": history.tail(7).mean(),
                    "rolling_14": history.tail(14).mean(),
                    "dayofweek": next_date.dayofweek,
                    "month": next_date.month,
                    "dayofyear": next_date.dayofyear
                }])

                predicted_arrival = max(
                    0,
                    float(final_model.predict(next_features[feature_columns])[0])
                )

                future_results.append({
                    "Date": next_date.strftime("%d-%m-%Y"),
                    "Predicted Arrival": round(predicted_arrival, 2)
                })

                history.loc[next_date] = predicted_arrival

            forecast_df = pd.DataFrame(future_results)

            st.dataframe(forecast_df, use_container_width=True)

            st.caption(
                "Forecast values are model estimates, not actual market arrivals. "
                "Missing historical dates were interpolated for model input."
            )

            

elif page == "Watchlist":

    st.divider()
    st.subheader("Saved Vegetables")

    items = api("/api/watchlist/")

    if isinstance(items, list):

        if not items:
            st.info("Your watchlist is empty.")

        for item in items:

            col1, col2 = st.columns([3, 1])

            col1.write(f"🥬 {item['commodity']}")

            if col2.button(
                "Remove",
                key=f"remove_{item['id']}"
            ):

                try:
                    response = requests.delete(
                        f"{API}/api/watchlist/{item['id']}",
                        headers={
                            "Authorization": (
                                f"Bearer {st.session_state.access_token}"
                            )
                        },
                        timeout=15
                    )

                    if response.status_code == 200:
                        st.success("Removed successfully!")
                        st.rerun()
                    else:
                        st.error("Unable to remove item.")

                except requests.RequestException:
                    st.error("Backend connection failed.")

    else:
        st.error(items.get("error", "Unable to load watchlist."))

elif page == "Price Alerts":


    st.title("🔔 Price Alerts")
    st.caption("Track vegetable prices and target alerts.")

    commodity = st.text_input(
        "Vegetable name",
        placeholder="Example: Tomato"
    )

    target_price = st.number_input(
        "Target price (₹ per quintal)",
        min_value=1,
        step=100
    )

    condition = st.selectbox(
        "Alert condition",
        ["above", "below"]
    )

    if st.button("Create Price Alert"):
        if not commodity.strip():
            st.warning("Enter a vegetable name.")
        else:
            try:
                response = requests.post(
                    f"{API}/api/alerts/",
                    json={
                        "commodity": commodity,
                        "target_price": int(target_price),
                        "condition": condition
                    },
                    headers={
                        "Authorization": (
                            f"Bearer {st.session_state.access_token}"
                        )
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    st.success("Price alert created successfully!")
                    st.rerun()
                else:
                    st.error(response.text)

            except requests.RequestException:
                st.error("Backend connection failed.")

    st.divider()
    st.subheader("My Active Alerts")

    try:
        response = requests.get(
            f"{API}/api/alerts/",
            headers={
                "Authorization": (
                    f"Bearer {st.session_state.access_token}"
                )
            },
            timeout=15
        )

        if response.status_code == 200:
            alerts = response.json()

            if not alerts:
                st.info("No price alerts created yet.")

            for alert in alerts:
                st.write(
                    f"🥬 {alert['commodity']} | "
                    f"Target: ₹{alert['target_price']} | "
                    f"Condition: {alert['condition']}"
                )

                if alert["current_price"] is not None:
                    st.write(
                        f"Current price: ₹{alert['current_price']:.2f}"
                    )

                if alert["is_triggered"]:
                    st.success("🔔 Target price reached!")

                if st.button(
                    "Delete Alert",
                    key=f"delete_alert_{alert['id']}"
                ):
                    delete_response = requests.delete(
                        f"{API}/api/alerts/{alert['id']}",
                        headers={
                            "Authorization": (
                                f"Bearer {st.session_state.access_token}"
                            )
                        },
                        timeout=15
                    )

                    if delete_response.status_code == 200:
                        st.success("Alert deleted!")
                        st.rerun()
                    else:
                        st.error("Unable to delete alert.")

        else:
            st.error("Unable to load alerts.")

    except requests.RequestException:
        st.error("Backend connection failed.")

elif page == "PDF Reports":

    st.title("📄 PDF Market Reports")
    st.caption("Download reports using real market price data.")

    commodity = st.text_input(
        "Commodity",
        placeholder="Example: Tomato"
    )

    state = st.text_input("State", value="All")
    market = st.text_input("Market", value="All")

    if st.button("Generate PDF Report"):

        if not commodity.strip():
            st.warning("Enter a commodity name.")

        else:
            try:
                response = requests.get(
                    f"{API}/api/reports/market",
                    params={
                        "commodity": commodity.strip(),
                        "state": state.strip(),
                        "market": market.strip()
                    },
                    headers={
                        "Authorization": (
                            f"Bearer {st.session_state.access_token}"
                        )
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    st.download_button(
                        "Download PDF",
                        data=response.content,
                        file_name="AgriSense_Market_Report.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error(response.text)

            except requests.RequestException:
                st.error("Backend connection failed.")
