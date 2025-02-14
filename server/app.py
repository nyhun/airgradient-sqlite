from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3
import numpy as np

# FastAPI app initialization
app = FastAPI()

# SQLite Database path
DB_PATH = "logs.db"

# Ensure the database and table exist
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wifi INTEGER,
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

    # Insert the new log into the database
    cursor.execute("INSERT INTO logs (wifi, pm02, rco2, atmp, rhum, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                   (log.wifi, log.pm02, log.rco2, log.atmp, log.rhum, timestamp))
    conn.commit()

    conn.close()

    return {"message": "Value logged successfully!"}

# GET endpoint to fetch data from the last 24 hours, averaged by 5-minute window
@app.get("/data")
async def get_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the data from the last 24 hours
    last_24_hours = datetime.now() - timedelta(hours=24)
    cursor.execute("SELECT wifi, pm02, rco2, atmp, rhum, timestamp FROM logs WHERE timestamp >= ?", 
                   (last_24_hours.strftime('%Y-%m-%d %H:%M:%S'),))
    rows = cursor.fetchall()

    conn.close()

    if not rows:
        return {"message": "No data available for the last 24 hours"}

    # Prepare the data by rounding timestamps to the nearest 5-minute interval
    time_intervals = {}
    for row in rows:
        timestamp = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S')
        interval = timestamp.replace(second=0, microsecond=0, minute=(timestamp.minute // 5) * 5)
        if interval not in time_intervals:
            time_intervals[interval] = {"pm02": [], "rco2": [], "atmp": [], "rhum": []}
        time_intervals[interval]["pm02"].append(row[1])
        time_intervals[interval]["rco2"].append(row[2])
        time_intervals[interval]["atmp"].append(row[3])
        time_intervals[interval]["rhum"].append(row[4])

    # Calculate the averages for each 5-minute window
    timestamps = []
    pm02_values = []
    rco2_values = []
    atmp_values = []
    rhum_values = []

    for interval, values in time_intervals.items():
        avg_pm02 = np.mean(values["pm02"])
        avg_rco2 = np.mean(values["rco2"])
        avg_atmp = np.mean(values["atmp"])
        avg_rhum = np.mean(values["rhum"])

        timestamps.append(interval.strftime('%A %H:%M'))
        pm02_values.append(avg_pm02)
        rco2_values.append(avg_rco2)
        atmp_values.append(avg_atmp)
        rhum_values.append(avg_rhum)

    # Return the averaged data for the charts
    data = {
        "timestamps": timestamps,
        "pm02": pm02_values,
        "rco2": rco2_values,
        "atmp": atmp_values,
        "rhum": rhum_values
    }

    return data

