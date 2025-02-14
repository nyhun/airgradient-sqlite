from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3

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
        value INTEGER,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

# Call this function to ensure the table exists
init_db()

{"wifi":-50,"pm02":38,"rco2":1060,"atmp":26.30,"rhum":28}

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
    values = [row[0] for row in rows]

    # Convert to a format that Chart.js can understand
    data = {
        "timestamps": [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps],
        "values": values
    }

    return data

# GET endpoint to render HTML page with Chart.js
@app.get("/", response_class=HTMLResponse)
async def get_chart():
    return HTMLResponse(content="""
    <html>
        <head>
            <title>Logged Values Chart</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Logged Values in Last 24 Hours</h1>
            <canvas id="myChart" width="400" height="200"></canvas>

            <script>
                fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const ctx = document.getElementById('myChart').getContext('2d');
                    const chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.timestamps,
                            datasets: [{
                                label: 'Logged Values',
                                data: data.values,
                                borderColor: 'rgb(75, 192, 192)',
                                fill: false,
                            }]
                        },
                        options: {
                            scales: {
                                x: {
                                    ticks: {
                                        maxRotation: 90,
                                        minRotation: 45
                                    }
                                }
                            }
                        }
                    });
                });
            </script>
        </body>
    </html>
    """)
