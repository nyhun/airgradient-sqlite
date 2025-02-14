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
        value INTEGER,
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

    # Insert the new log into the database
    cursor.execute("INSERT INTO logs (value, timestamp) VALUES (?, ?)", (log.rco2, timestamp))
    conn.commit()

    conn.close()

    return {"message": "Value logged successfully!"}

# GET endpoint to fetch data from the last 24 hours
@app.get("/data")
async def get_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the data from the last 24 hours
    last_24_hours = datetime.now() - timedelta(hours=24)
    cursor.execute("SELECT value, timestamp FROM logs WHERE timestamp >= ?", (last_24_hours.strftime('%Y-%m-%d %H:%M:%S'),))
    rows = cursor.fetchall()

    conn.close()

    if not rows:
        return {"message": "No data available for the last 24 hours"}

    # Prepare data for the chart
    timestamps = [datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S') for row in rows]
    pm02 = [row[0] for row in rows]
    rco2 = [row[0] for row in rows]
    atmp = [row[0] for row in rows]
    rhum = [row[0] for row in rows]

    # Convert to a format that Chart.js can understand
    data = {
        "timestamps": [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps],
        "pm02": pm02,
        "rco2": rco2,
        "atmp": atmp,
        "rhum": rhum
    }

    return data

# GET endpoint to render HTML page with Chart.js using Jinja2 templates
@app.get("/", response_class=HTMLResponse)
async def get_chart(request: Request):
    return templates.TemplateResponse("chart_template.html", {"request": request})

