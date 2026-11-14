import streamlit as st
import requests
import pandas as pd
import plotly.express as px

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
        response = requests.get(
            API + path,
            params=params,
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

if health.get("error"):
    st.error(
        "Backend is not running. "
        "Please start the backend and refresh this page."
    )
    st.stop()


# -----------------------------
# SIDEBAR
# -----------------------------

with st.sidebar:
    st.header("Control Center")

    page = st.radio(
        "Navigate",
        [
            "Market Overview",
            "Historical Analysis",
            "Future Forecast",
            "Weather Intelligence",
            "AI Price Insights",
            "AI Chatbot",
            "Data & Model Lab"
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

    st.subheader("💬 AgriSense market assistant")

    st.caption(
        "Grounded answers from the loaded real CSV. "
        "No external LLM key is configured."
    )

    question = st.chat_input(
        "Ask: What is latest tomato price? Why is price changing?"
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

        chat_params = {
            **params,
            "commodity": requested_vegetable
        }

        chat_summary = api(
            "/api/summary",
            chat_params
        )

        if any(
            keyword in question_lower
            for keyword in [
                "why", "increase", "decrease",
                "rise", "fall"
            ]
        ):

            if df.empty or "date" not in df.columns:
                answer = (
                    "No matching daily data is available to analyse "
                    "price movement."
                )

            elif df["date"].nunique() < 2:

                answer = (
                    "The uploaded dataset has only one date "
                    "for this selected series, so I cannot "
                    "calculate a movement or identify its cause. "
                    "Add historical market data and verified "
                    "weather/transport/supply datasets."
                )

            else:

                answer = (
                    "I can compare observed movement and model "
                    "features, but cannot prove weather, transport, "
                    "season or supply-demand caused it without "
                    "matched verified driver datasets."
                )
        elif "lowest" in question_lower or "minimum" in question_lower:

            if (
                not df.empty
                and "market" in df.columns
                and "modal_price" in df.columns
            ):
                latest_date = df["date"].max()
                latest_data = df[df["date"] == latest_date].copy()

                latest_data["modal_price"] = pd.to_numeric(
                    latest_data["modal_price"],
                    errors="coerce"
                )

                latest_data = latest_data.dropna(
                    subset=["modal_price"]
                )

                if not latest_data.empty:
                    lowest = latest_data.loc[
                        latest_data["modal_price"].idxmin()
                    ]

                    answer = (
                        f"Lowest modal price is "
                        f"{money(lowest['modal_price'])} per quintal "
                        f"at {lowest['market']} on "
                        f"{latest_date.strftime('%Y-%m-%d')}."
                    )
                else:
                    answer = "No valid market price records found."
            else:
                answer = "Market price data is unavailable."
        elif "highest" in question_lower or "maximum" in question_lower:

            if (
                not df.empty
                and "market" in df.columns
                and "modal_price" in df.columns
            ):
                latest_date = df["date"].max()

                latest_data = df[df["date"] == latest_date].copy()

                latest_data["modal_price"] = pd.to_numeric(
                    latest_data["modal_price"],
                    errors="coerce"
                )

                latest_data = latest_data.dropna(
                    subset=["modal_price"]
                )

                if not latest_data.empty:
                    highest = latest_data.loc[
                        latest_data["modal_price"].idxmax()
                    ]

                    answer = (
                        f"Highest Amaranthus modal price is "
                        f"{money(highest['modal_price'])} per quintal "
                        f"at {highest['market']} on "
                        f"{latest_date.strftime('%Y-%m-%d')}."
                    )
                else:
                    answer = "No valid market price records found."
            else:
                answer = "Market price data is unavailable."

        elif any(
            keyword in question_lower
            for keyword in ["price", "rate", "cost"]
        ):

            if chat_summary.get("available"):

                answer = (
                    f"Average {requested_vegetable} modal price is "
                    f"{money(chat_summary.get('modal_price'))} "
                    f"per quintal on {chat_summary.get('date', 'N/A')}, "
                    f"averaged across {chat_summary.get('records', 0)} "
                    f"market records in {chat_summary.get('markets', 0)} "
                    f"markets. "
                    f"Price range: {money(chat_summary.get('min_price'))} "
                    f"to {money(chat_summary.get('max_price'))}."
                )

            else:

                answer = (
                    f"No matching real market price data found "
                    f"for {requested_vegetable}."
                )

        elif "weather" in question_lower:

            answer = (
                "Open Weather Intelligence and fetch the latest "
                "Open-Meteo conditions for a location."
            )

        else:

            answer = (
                "I can answer latest loaded prices, data coverage, "
                "forecast readiness and observed price movement. "
                "Try asking for the latest price or why a change "
                "cannot yet be explained."
            )

        st.chat_message("assistant").write(answer)


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

    st.markdown("**Model comparison**")

    if st.button("Compare baseline models"):

        comparison_result = api(
            "/api/model-comparison",
            params
        )

        models = comparison_result.get("models", [])

        if models:

            st.dataframe(
                pd.DataFrame(models),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "At least 50 engineered daily observations "
                "are required for chronological model comparison."
            )

    st.markdown("**Feature implementation status**")

    feature_status = [
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
            "Not installed; baseline feature importance only"
        ),
        (
            "XGBoost / LightGBM / SARIMA / LSTM / TFT",
            "Not yet implemented"
        ),
        (
            "RAG LLM chatbot",
            "Not yet implemented"
        ),
        (
            "Automated alerts / authentication / watchlists",
            "Not yet implemented"
        ),
        (
            "PDF reports / maps / supply forecasting",
            "Not yet implemented"
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
