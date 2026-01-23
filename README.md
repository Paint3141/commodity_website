markdown

# Draudes Data - Commodity Prices Dashboard

A modern, interactive web dashboard for tracking commodity prices (Bitcoin, Gold, Silver, Palladium, Copper, Platinum) with historical charts and percentage change overview.

Built with **FastAPI** + **Highcharts** + **Bootstrap 5**.

## ✨ Features

- **Interactive Price Chart**: View any commodity in multiple currencies and time periods (1d to 5y)
- **Commodity Ratio Chart**: Compare two commodities (e.g., Gold/Silver ratio)
- **Logarithmic scale toggle** for both charts
- **Sidebar Overview Table** (USD only):
  - Current price (2 decimal places)
  - 7-day, 1-month, and 1-year % change
  - Color-coded gains (green) / losses (red)
- **Responsive design**: Sidebar hidden on mobile/small screens
- **Multi-currency support** (USD, GBP, EUR, CNY, JPY, RUB) via historical FX rates
- Data loads on page refresh (no live WebSocket updates)

## 🛠️ Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Frontend**: Bootstrap 5.3, Highcharts.js (via CDN), vanilla JavaScript
- **Database**: PostgreSQL (via SQLAlchemy)
- **Templating**: Jinja2
- **Environment**: python-dotenv

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL database
- Required tables in database:
  - `commodityprice` (columns: `symbol`, `fetched_at`, `usd_price`)
  - `fxrate` (columns: `currency`, `fetched_at`, `rate_vs_usd`)

## 🚀 Installation & Setup

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd commodity_website

2. Create and activate virtual environment:
   ```bash
    python -m venv env
    source env/bin/activate    # On Windows: env\Scripts\activate

3. Install dependencies:
    ```bash
    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv jinja2

4. Create .env file in root:
    ```
    DATABASE_URL=postgresql://username:password@localhost:5432/commodity_db


## Running the App:

    ```bash
    uvicorn app:app --reload
    Open browser → http://127.0.0.1:8000 

## Project Structure

    ```
    commodity_website/
    ├── app.py                    # FastAPI backend + API endpoints
    ├── templates/
    │   ├── base.html            # Base layout (navbar + footer)
    │   ├── index.html           # Main dashboard (charts + sidebar)
    │   └── cv.html              # CV page
    ├── static/                   # (optional) static files
    ├── .env
    └── README.md

## API EndpointsGET / → Main dashboard
GET /cv → CV page
GET /api/data/{commodities} → Price data for chart (supports comma-separated symbols)
GET /api/summary → Current prices + % changes for sidebar table

## Customization
Add new commodities → update name mapping in fetch_commodity_summary() in app.py
Change default commodities → edit <select> options in index.html
Modify sidebar columns → edit loadCommodityTable() function
Add more currencies → ensure fxrate table has data for them

## Notes
Price formatting: Bitcoin = 2 decimals, others = 2 decimals (forced in frontend)
Charts use ISO date strings for Highcharts compatibility
No live updates — data refreshes on page reload

## License 
Personal / educational use.