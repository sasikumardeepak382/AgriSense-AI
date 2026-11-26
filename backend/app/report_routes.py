
from io import BytesIO
from datetime import datetime

import pandas as pd

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from .data import load_data
from .auth_routes import require_user


router = APIRouter(
    prefix="/api/reports",
    tags=["PDF Reports"]
)


@router.get("/market")
def generate_market_report(
    commodity: str,
    state: str = "All",
    market: str = "All",
    user=Depends(require_user)
):
    df = load_data()

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No real market data available."
        )

    df = df.copy()

    df = df[
        df["commodity"].str.casefold() == commodity.casefold()
    ]

    if state.casefold() != "all":
        df = df[
            df["state"].str.casefold() == state.casefold()
        ]

    if market.casefold() != "all":
        df = df[
            df["market"].str.casefold() == market.casefold()
        ]

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No matching real market records found."
        )

    df["modal_price"] = pd.to_numeric(
        df["modal_price"], errors="coerce"
    )

    df["min_price"] = pd.to_numeric(
        df["min_price"], errors="coerce"
    )

    df["max_price"] = pd.to_numeric(
        df["max_price"], errors="coerce"
    )

    df["date"] = pd.to_datetime(
        df["date"], errors="coerce"
    )

    df = df.dropna(subset=["date", "modal_price"])

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No valid price records found."
        )

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date]

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph("AgriSense AI - Market Price Report", styles["Title"])
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            f"Commodity: {commodity}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"State: {state} | Market: {market}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"Report Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"Latest Source Date: {latest_date.strftime('%d-%m-%Y')}",
            styles["Normal"]
        )
    )

    story.append(Spacer(1, 18))

    story.append(
        Paragraph("Latest Market Summary", styles["Heading2"])
    )

    summary_data = [
        ["Metric", "Value"],
        ["Latest Minimum Price", f"INR {latest['min_price'].min():,.2f}"],
        ["Latest Maximum Price", f"INR {latest['max_price'].max():,.2f}"],
        ["Average Modal Price", f"INR {latest['modal_price'].mean():,.2f}"],
        ["Markets Available", str(latest["market"].nunique())],
        ["Total Records", str(len(df))]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[3 * inch, 2.5 * inch]
    )

    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT")
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 20))

    story.append(
        Paragraph("Recent Price Records", styles["Heading2"])
    )

    recent = df.sort_values(
        "date", ascending=False
    ).head(15)

    table_data = [
        ["Date", "Market", "Min", "Max", "Modal"]
    ]

    for _, row in recent.iterrows():
        table_data.append([
            row["date"].strftime("%d-%m-%Y"),
            str(row["market"])[:22],
            f"{row['min_price']:,.0f}" if pd.notna(row["min_price"]) else "N/A",
            f"{row['max_price']:,.0f}" if pd.notna(row["max_price"]) else "N/A",
            f"{row['modal_price']:,.0f}"
        ])

    records_table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            1.1 * inch,
            1.8 * inch,
            0.8 * inch,
            0.8 * inch,
            0.9 * inch
        ]
    )

    records_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("PADDING", (0, 0), (-1, -1), 6)
    ]))

    story.append(records_table)
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Source: AgriSense AI real market CSV dataset. "
            "Prices are source values in INR per quintal. "
            "This report does not contain synthetic or forecast values.",
            styles["Italic"]
        )
    )

    document.build(story)

    buffer.seek(0)

    filename = f"AgriSense_{commodity}_Market_Report.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
