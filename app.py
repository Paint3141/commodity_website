from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from datetime import date, timedelta
import os

app = FastAPI()

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g., postgresql://user:pass@host/dbname
engine = create_engine(DATABASE_URL)

# Mount static files (put Highcharts JS here later, and cv.pdf)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Helper to fetch data (adjusted to support multiple commodities)
def fetch_commodity_data(commodities: list, currency: str = "USD", days: int = 365):
    try:
        with engine.connect() as conn:
            series = []
            for commodity in commodities:
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

                series.append({"name": f"{commodity} in {currency}", "data": series_data})

            return {"series": series}

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")

# Add this new function (place near fetch_commodity_data)
def fetch_commodity_summary():
    symbols_query = text("SELECT DISTINCT symbol FROM commodityprice ORDER BY symbol")
    with engine.connect() as conn:
        symbols = [row[0] for row in conn.execute(symbols_query).fetchall()]
        
        summary = []
        today = date.today()
        
        for symbol in symbols:
            # Latest price
            latest_q = text("""
                SELECT usd_price, fetched_at 
                FROM commodityprice 
                WHERE symbol = :symbol 
                ORDER BY fetched_at DESC 
                LIMIT 1
            """)
            latest = conn.execute(latest_q, {"symbol": symbol}).fetchone()
            if not latest or latest.usd_price is None:
                continue
                
            current_price = float(latest.usd_price)
            current_date = latest.fetched_at.date()
            
            # Helper to get price on or before a target date
            def get_price_before(target_date):
                q = text("""
                    SELECT usd_price 
                    FROM commodityprice 
                    WHERE symbol = :symbol 
                      AND CAST(fetched_at AS DATE) <= :target_date
                    ORDER BY fetched_at DESC 
                    LIMIT 1
                """)
                row = conn.execute(q, {"symbol": symbol, "target_date": target_date}).fetchone()
                return float(row.usd_price) if row and row.usd_price is not None else None
            
            # Calculate % changes
            price_7d = get_price_before(today - timedelta(days=7))
            price_1m = get_price_before(today - timedelta(days=30))
            price_1y = get_price_before(today - timedelta(days=365))
            
            change_7d = round(((current_price - price_7d) / price_7d) * 100, 2) if price_7d else None
            change_1m = round(((current_price - price_1m) / price_1m) * 100, 2) if price_1m else None
            change_1y = round(((current_price - price_1y) / price_1y) * 100, 2) if price_1y else None
            
            # Price formatting
            if symbol == "BTC":
                price_display = round(current_price, 2)
            else:
                price_display = round(current_price, 4)   # Gold, Silver, Palladium, Copper
                
            summary.append({
                "symbol": symbol,
                "name": {
                    "BTC": "Bitcoin",
                    "XAU": "Gold",
                    "XAG": "Silver",
                    "XPD": "Palladium",
                    "XPT": "Platinum",
                    "HG": "Copper"
                }.get(symbol, symbol),
                "price": price_display,
                "change_7d": change_7d,
                "change_1m": change_1m,
                "change_1y": change_1y
            })
        
        return summary

# Main page (Home)
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# CV page
@app.get("/cv", response_class=HTMLResponse)
async def cv(request: Request):
    return templates.TemplateResponse("cv.html", {"request": request})

# API for data (modified to accept comma-separated commodities)
@app.get("/api/data/{commodities}")
async def get_data(commodities: str, currency: str = "USD", period: str = "1y"):
    commodity_list = [c.strip().upper() for c in commodities.split(',')]
    days_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = days_map.get(period, 365)
    
    result = fetch_commodity_data(commodity_list, currency.upper(), days)
    return result   # ← {"series": [{"name": ..., "data": [[ts, val], ...]}, ...]}

# Endpoint for commodity summary table side panel 
@app.get("/api/summary")
async def get_summary():
    try:
        data = fetch_commodity_summary()
        return {"commodities": data}
    except Exception as e:
        return {"error": str(e)}