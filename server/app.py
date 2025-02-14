from fastapi import FastAPI, Request
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
        atmp INTEGER,
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
    atmp: int
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

# GET endpoint to fetch data from the last 24 hours
@app.get("/data")
async def get_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the data from the last 24 hours
    last_24_hours = datetime.now() - timedelta(hours=24)
    cursor.execute("SELECT pm02, rco2, atmp, rhum, timestamp FROM logs WHERE timestamp >= ?", 
                   (last_24_hours.strftime('%Y-%m-%d %H:%M:%S'),))
    rows = cursor.fetchall()

    conn.close()

    if not rows:
        return {"message": "No data available for the last 24 hours"}

    # Group data by 5-minute windows
    data = defaultdict(list)
    for row in rows:
        # Extract the timestamp and convert it to a datetime object
        timestamp = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S')
        # Round down to the nearest 5-minute mark
        timestamp_rounded = timestamp.replace(second=0, microsecond=0)
        timestamp_rounded -= timedelta(minutes=timestamp_rounded.minute % 5)
        
        # Append values to their respective time window (rounded to 5 minutes)
        data[timestamp_rounded].append({
            'pm02': row[0],
            'rco2': row[1],
            'atmp': row[2],
            'rhum': row[3]
        })

    # Calculate the average for each 5-minute window
    averages = []
    for timestamp, values in data.items():
        avg_pm02 = sum(v['pm02'] for v in values) / len(values)
        avg_rco2 = sum(v['rco2'] for v in values) / len(values)
        avg_atmp = sum(v['atmp'] for v in values) / len(values)
        avg_rhum = sum(v['rhum'] for v in values) / len(values)

        averages.append({
            'timestamp': timestamp,
            'avg_pm02': avg_pm02,
            'avg_rco2': avg_rco2,
            'avg_atmp': avg_atmp,
            'avg_rhum': avg_rhum
        })

    # Format the data for Chart.js
    chart_data = {
        "timestamps": [ts.strftime('%A %H:%M') for ts in [avg['timestamp'] for avg in averages]],
        "avg_pm02": [avg['avg_pm02'] for avg in averages],
        "avg_rco2": [avg['avg_rco2'] for avg in averages],
        "avg_atmp": [avg['avg_atmp'] for avg in averages],
        "avg_rhum": [avg['avg_rhum'] for avg in averages]
    }

    return chart_data

# GET endpoint to render HTML page with Chart.js using Jinja2 templates
@app.get("/", response_class=HTMLResponse)
async def get_chart(request: Request):
    return templates.TemplateResponse("chart_template.html", {"request": request})

