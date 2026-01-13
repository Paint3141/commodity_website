from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
import datetime  # For time ranges

app = FastAPI()

# Mount static files (put Highcharts JS here later)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Helper to fetch data (adjust table/column names as needed)
def fetch_commodity_data(commodity: str, currency: str = "USD", days: int = 365):
    try:
        with engine.connect() as conn:
            # Fetch commodity prices (assume table 'commodities' with date, commodity, price_usd)
            query = text("""
                SELECT fetched_at AS date_time, usd_price 
                FROM commodityprice 
                WHERE commodity = :commodity AND fetched_at >= :start_date 
                ORDER BY fetched_at ASC
            """)
            start_date = datetime.date.today() - datetime.timedelta(days=days)
            result = conn.execute(query, {"commodity": commodity, "start_date": start_date}).fetchall()
            
            data = [{"date": row[0].isoformat(), "price_usd": row[1]} for row in result]
            
            # If currency != USD, fetch latest rates (assume daily rates; use latest for simplicity)
            if currency != "USD":
                rate_query = text("""
                    SELECT rate_vs_usd 
                    FROM fxrate 
                    WHERE currency = :currency 
                    ORDER BY date DESC LIMIT 1
                """)
                rate_result = conn.execute(rate_query, {"currency": currency}).scalar()
                if rate_result:
                    # Assuming rate is target_currency per 1 USD (e.g., GBP per USD)
                    # Convert: price_in_currency = price_usd * rate
                    for item in data:
                        item["price"] = item["price_usd"] * rate_result
                    del item["price_usd"]  # Clean up
                else:
                    raise ValueError(f"No rate found for {currency}")
            else:
                for item in data:
                    item["price"] = item["price_usd"]
                    del item["price_usd"]
            
            return data
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}")

# Main page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# API for data
@app.get("/api/data/{commodity}")
async def get_data(commodity: str, currency: str = "USD", period: str = "1y"):
    days_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = days_map.get(period, 365)
    data = fetch_commodity_data(commodity.upper(), currency.upper(), days)
    return {"series": [{"name": f"{commodity} in {currency}", "data": [[item["date"], item["price"]] for item in data]}]}