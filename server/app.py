from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3

# FastAPI app initialization
app = FastAPI()

# Jinja2 Template setup
templates = Jinja2Templates(directory="templates")

# SQLite Database path
DB_PATH = "logs.db"

# Ensure the database and table exist
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pm02 INTEGER,
        rco2 INTEGER,
        atmp FLOAT,
        rhum INTEGER,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

# Call this function to ensure the table exists
init_db()

class Log(BaseModel):
    wifi: int
    pm02: int
    rco2: int
    atmp: float
    rhum: int

# POST endpoint to log a number with timestamp
@app.post("/log")
async def log_number(log: Log):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Insert the new log into the database for each metric
    cursor.execute("INSERT INTO logs (pm02, rco2, atmp, rhum, timestamp) VALUES (?, ?, ?, ?, ?)", 
                   (log.pm02, log.rco2, log.atmp, log.rhum, timestamp))
    conn.commit()

    conn.close()

    return {"message": "Values logged successfully!"}

# Aggregation window in minutes for each supported timespan
WINDOW_MINUTES = {
    8: 5,
    24: 15,
    48: 30,
    72: 45,
    96: 60,
    120: 75,
    144: 90,
    168: 105,
}

# GET endpoint to fetch data for a configurable timespan
@app.get("/data")
async def get_data(hours: int = 24):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if hours not in WINDOW_MINUTES:
        raise HTTPException(status_code=422, detail=f"Invalid hours value. Must be one of: {sorted(WINDOW_MINUTES)}")
    window_minutes = WINDOW_MINUTES[hours]

    since = datetime.now() - timedelta(hours=hours)
    cursor.execute(
        "SELECT pm02, rco2, atmp, rhum, timestamp FROM logs WHERE timestamp >= ? ORDER BY timestamp",
        (since.strftime('%Y-%m-%d %H:%M:%S'),)
    )
    rows = cursor.fetchall()

    conn.close()

    if not rows:
        return {"message": f"No data available for the last {hours} hours"}

    # Group data by window_minutes intervals and calculate averages
    grouped_data = []
    current_window = None
    current_window_data = []

    for row in rows:
        timestamp = datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S')

        # Round down to the nearest window_minutes boundary (works for windows > 60 min too)
        total_minutes = timestamp.hour * 60 + timestamp.minute
        floor_minutes = (total_minutes // window_minutes) * window_minutes
        timestamp_rounded = timestamp.replace(
            hour=floor_minutes // 60,
            minute=floor_minutes % 60,
            second=0,
            microsecond=0
        )
        
        if current_window and current_window != timestamp_rounded:
            # Calculate averages for the current window
            avg_pm02 = sum(item['pm02'] for item in current_window_data) / len(current_window_data)
            avg_rco2 = sum(item['rco2'] for item in current_window_data) / len(current_window_data)
            avg_atmp = sum(item['atmp'] for item in current_window_data) / len(current_window_data)
            avg_rhum = sum(item['rhum'] for item in current_window_data) / len(current_window_data)
            
            # Append the result to grouped_data
            grouped_data.append({
                'timestamp': current_window,
                'avg_pm02': avg_pm02,
                'avg_rco2': avg_rco2,
                'avg_atmp': avg_atmp,
                'avg_rhum': avg_rhum
            })
            
            # Reset the window data
            current_window_data = []

        # Add the current row's data to the window data
        current_window = timestamp_rounded
        current_window_data.append({
            'pm02': row[0],
            'rco2': row[1],
            'atmp': row[2],
            'rhum': row[3]
        })

    # Final window processing (if any data is left)
    if current_window_data:
        avg_pm02 = sum(item['pm02'] for item in current_window_data) / len(current_window_data)
        avg_rco2 = sum(item['rco2'] for item in current_window_data) / len(current_window_data)
        avg_atmp = sum(item['atmp'] for item in current_window_data) / len(current_window_data)
        avg_rhum = sum(item['rhum'] for item in current_window_data) / len(current_window_data)
        
        grouped_data.append({
            'timestamp': current_window,
            'avg_pm02': avg_pm02,
            'avg_rco2': avg_rco2,
            'avg_atmp': avg_atmp,
            'avg_rhum': avg_rhum
        })

    # Prepare data for Chart.js (timestamps formatted as 'Day Hour:Minute')
    chart_data = {
        "timestamps": [ts.strftime('%A %H:%M') for ts in [entry['timestamp'] for entry in grouped_data]],
        "pm02": [entry['avg_pm02'] for entry in grouped_data],
        "rco2": [entry['avg_rco2'] for entry in grouped_data],
        "atmp": [entry['avg_atmp'] for entry in grouped_data],
        "rhum": [entry['avg_rhum'] for entry in grouped_data]
    }

    return chart_data

# GET endpoint to render HTML page with Chart.js using Jinja2 templates
@app.get("/", response_class=HTMLResponse)
async def get_chart(request: Request):
    return templates.TemplateResponse("chart_template.html", {"request": request})

