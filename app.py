from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine,text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from datetime import date, timedelta
import os

app = FastAPI()

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g., postgresql://user:pass@host/dbname
engine = create_engine(DATABASE_URL)

# Mount static files (put Highcharts JS here later)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Helper to fetch data (adjust table/column names as needed)
def fetch_commodity_data(commodity: str, currency: str = "USD", days: int = 365):
    try:
        with engine.connect() as conn:
            if currency == "USD":
                # Simple case — no join needed
                query = text("""
                    SELECT c.fetched_at AS date, c.usd_price AS price
                    FROM commodityprice c
                    WHERE c.symbol = :commodity
                      AND c.fetched_at >= :start_date
                    ORDER BY c.fetched_at ASC
                """)
                params = {"commodity": commodity, "start_date": date.today() - timedelta(days=days)}
            else:
                # Join on date for historical conversion
                query = text("""
                    SELECT 
                        c.fetched_at AS date,
                        c.usd_price * er.rate_vs_usd AS price
                    FROM commodityprice c
                    LEFT JOIN fxrate er 
                        ON er.currency = :currency 
                       AND CAST(c.fetched_at AS DATE) = CAST(er.fetched_at AS DATE)          -- exact date match
                    WHERE c.symbol = :commodity
                      AND c.fetched_at >= :start_date
                    ORDER BY c.fetched_at ASC
                """)
                params = {
                    "commodity": commodity,
                    "currency": currency,
                    "start_date": date.today() - timedelta(days=days)
                }

            result = conn.execute(query, params).fetchall()
            
            # Format for Highcharts: [[timestamp_ms or iso, value], ...]
            series_data = []
            for row in result:
                dt = row[0]
                price = float(row[1]) if row[1] is not None else None
                # Use ISO string — Highcharts understands it
                series_data.append([dt.isoformat(), price])

            return {"series": [{"name": f"{commodity} in {currency}", "data": series_data}]}

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")

# Main page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# API for data
# @app.get("/api/data/{commodity}")
# async def get_data(commodity: str, currency: str = "USD", period: str = "1y"):
#     days_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1825}
#     days = days_map.get(period, 365)
#     data = fetch_commodity_data(commodity.upper(), currency.upper(), days)
#     return {"series": [{"name": f"{commodity} in {currency}", "data": [[item["date"], item["price"]] for item in data]}]}

@app.get("/api/data/{commodity}")
async def get_data(commodity: str, currency: str = "USD", period: str = "1y"):
    days_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = days_map.get(period, 365)
    
    result = fetch_commodity_data(commodity.upper(), currency.upper(), days)
    return result   # ← already has {"series": [{"name": ..., "data": [[ts, val], ...]}]}