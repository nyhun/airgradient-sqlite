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

# GET endpoint to fetch data from the last 24 hours for each metric
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

    # Prepare data for the chart
    timestamps = [datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S') for row in rows]
    pm02_values = [row[0] for row in rows]
    rco2_values = [row[1] for row in rows]
    atmp_values = [row[2] for row in rows]
    rhum_values = [row[3] for row in rows]

    # Convert to a format that Chart.js can understand
    data = {
        "timestamps": [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps],
        "pm02": pm02_values,
        "rco2": rco2_values,
        "atmp": atmp_values,
        "rhum": rhum_values
    }

    return data

# GET endpoint to render HTML page with multiple charts
@app.get("/", response_class=HTMLResponse)
async def get_chart():
    return HTMLResponse(content=f"""
    <html>
        <head>
            <title>Logged Values Charts</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Logged Values in Last 24 Hours</h1>

            <h2>PM02</h2>
            <canvas id="pm02Chart" width="400" height="200"></canvas>

            <h2>RCO2</h2>
            <canvas id="rco2Chart" width="400" height="200"></canvas>

            <h2>ATMP</h2>
            <canvas id="atmpChart" width="400" height="200"></canvas>

            <h2>RHUM</h2>
            <canvas id="rhumChart" width="400" height="200"></canvas>

            <script>
                fetch('/data')
                .then(response => response.json())
                .then(data => {{
                    const pm02Ctx = document.getElementById('pm02Chart').getContext('2d');
                    new Chart(pm02Ctx, {{
                        type: 'line',
                        data: {{
                            labels: data.timestamps,
                            datasets: [{{
                                label: 'PM02',
                                data: data.pm02,
                                borderColor: 'rgb(75, 192, 192)',
                                fill: false,
                            }}]
                        }},
                        options: {{
                            scales: {{
                                x: {{
                                    ticks: {{
                                        maxRotation: 90,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});

                    const rco2Ctx = document.getElementById('rco2Chart').getContext('2d');
                    new Chart(rco2Ctx, {{
                        type: 'line',
                        data: {{
                            labels: data.timestamps,
                            datasets: [{{
                                label: 'RCO2',
                                data: data.rco2,
                                borderColor: 'rgb(255, 99, 132)',
                                fill: false,
                            }}]
                        }},
                        options: {{
                            scales: {{
                                x: {{
                                    ticks: {{
                                        maxRotation: 90,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});

                    const atmpCtx = document.getElementById('atmpChart').getContext('2d');
                    new Chart(atmpCtx, {{
                        type: 'line',
                        data: {{
                            labels: data.timestamps,
                            datasets: [{{
                                label: 'ATMP',
                                data: data.atmp,
                                borderColor: 'rgb(54, 162, 235)',
                                fill: false,
                            }}]
                        }},
                        options: {{
                            scales: {{
                                x: {{
                                    ticks: {{
                                        maxRotation: 90,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});

                    const rhumCtx = document.getElementById('rhumChart').getContext('2d');
                    new Chart(rhumCtx, {{
                        type: 'line',
                        data: {{
                            labels: data.timestamps,
                            datasets: [{{
                                label: 'RHUM',
                                data: data.rhum,
                                borderColor: 'rgb(153, 102, 255)',
                                fill: false,
                            }}]
                        }},
                        options: {{
                            scales: {{
                                x: {{
                                    ticks: {{
                                        maxRotation: 90,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});
                }});
            </script>
        </body>
    </html>
    """)