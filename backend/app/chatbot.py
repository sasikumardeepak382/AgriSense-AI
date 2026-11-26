
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai

from .data import load_data, load_2025_data

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def retrieve_market_context(
    question: str,
    commodity: str | None = None,
    state: str = "All",
    market: str = "All",
    top_k: int = 12
):
    """Retrieve relevant real market records from the CSV."""

    question_lower = question.casefold()

    # Select the correct dataset based on requested year
    if "2025" in question_lower:
        df = load_2025_data()
    else:
        df = load_data()

        if df.empty:
         return None, "No valid modal price records were found."

    latest_date = df["date"].max()

    # Monthly average price analysis
    if "monthly" in question_lower and "average" in question_lower:

        monthly = (
            df.groupby(df["date"].dt.to_period("M"))
            .agg(
                average_modal_price=("modal_price", "mean"),
                records_count=("modal_price", "count")
            )
            .round(2)
            .reset_index()
        )

        monthly["month"] = monthly["date"].astype(str)

        records = monthly[
            ["month", "average_modal_price", "records_count"]
        ]

    else:
        latest = df.copy()

        if any(word in question_lower for word in ["lowest", "minimum"]):
            records = latest.nsmallest(top_k, "modal_price")

        elif any(word in question_lower for word in ["highest", "maximum"]):
            records = latest.nlargest(top_k, "modal_price")

        else:
            records = df.sort_values(
                "date", ascending=False
            ).head(top_k)

        records = records[
            [
                "date", "commodity", "state", "district",
                "market", "min_price", "max_price",
                "modal_price", "arrival"
            ]
        ].fillna("Not available")

    context = {
        "commodity": commodity or "Selected commodity",
        "latest_date": str(latest_date.date()),
        "available_dates": int(df["date"].nunique()),
        "total_matching_records": len(df),
        "retrieved_records": records.to_dict(orient="records")
    }

    return context, None
def ask_agrisense(
    question: str,
    commodity: str | None = None,
    state: str = "All",
    market: str = "All"
):
    """RAG retrieval followed by Gemini answer generation."""

    context, error = retrieve_market_context(
        question, commodity, state, market
    )

    if error:
        return {
            "answer": error,
            "sources": [],
            "model": MODEL_NAME
        }

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "answer": "Gemini API key is not configured.",
            "sources": [],
            "model": MODEL_NAME
        }

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are AgriSense AI, an agricultural market assistant.

Answer the user's question using ONLY the retrieved market data below.

Rules:
1. Never invent prices, dates, markets, arrivals or causes.
2. Mention the date and market when relevant.
3. Prices are in Indian Rupees per quintal.
4. If the retrieved data cannot answer the question,
   clearly say that the information is unavailable.
5. Do not claim weather, transport or supply-demand caused
   a price change unless verified evidence is provided.
6. Explain in simple, clear language.

RETRIEVED REAL MARKET DATA:
{context}

USER QUESTION:
{question}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        answer = response.text or "Gemini returned an empty response."

        return {
            "answer": answer,
            "sources": context["retrieved_records"],
            "model": MODEL_NAME,
            "retrieved_date": context["latest_date"]
        }

    except Exception as exc:
        return {
            "answer": f"Gemini API error: {str(exc)}",
            "sources": context["retrieved_records"],
            "model": MODEL_NAME
        }
