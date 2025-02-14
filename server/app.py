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

@app.get("/", response_class=HTMLResponse)
async def get_chart():
    return HTMLResponse(content=f"""
    <html>
        <head>
            <title>Logged Values Charts</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                }}
                .chart-container {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                    width: 100%;
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                canvas {{
                    width: 100% !important;
                    height: 250px !important;
                }}
                h1 {{
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                h2 {{
                    font-size: 20px;
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <h1>Logged Values in Last 24 Hours</h1>

            <div class="chart-container">
                <div>
                    <h2>PM02</h2>
                    <canvas id="pm02Chart"></canvas>
                </div>
                <div>
                    <h2>RCO2</h2>
                    <canvas id="rco2Chart"></canvas>
                </div>
                <div>
                    <h2>ATMP</h2>
                    <canvas id="atmpChart"></canvas>
                </div>
                <div>
                    <h2>RHUM</h2>
                    <canvas id="rhumChart"></canvas>
                </div>
            </div>

            <script>
                fetch('/data')
                .then(response => response.json())
                .then(data => {{
                    function getLineColor(value) {{
                        return value > 100 ? 'rgb(255, 99, 132)' : 'rgb(75, 192, 192)';
                    }}

                    const pm02Ctx = document.getElementById('pm02Chart').getContext('2d');
                    new Chart(pm02Ctx, {{
                        type: 'line',
                        data: {{
                            labels: data.timestamps,
                            datasets: [{{
                                label: 'PM02',
                                data: data.pm02,
                                borderColor: data.pm02.map(getLineColor),
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
                            }},
                            plugins: {{
                                annotation: {{
                                    annotations: {{
                                        line: {{
                                            type: 'line',
                                            yMin: 100,
                                            yMax: 100,
                                            borderColor: 'rgb(0, 0, 0)',
                                            borderWidth: 2,
                                            label: {{
                                                content: 'Value 100',
                                                enabled: true,
                                                position: 'center',
                                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                                font: {{
                                                    size: 12
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});

                    // Define the colors based on RCO2 values
                    function getRCO2LineColor(value) {{
                        if (value >= 400 && value <= 1000) {{
                            return 'rgb(75, 192, 192)';  // Green (Good)
                        }} else if (value > 1000 && value <= 2000) {{
                            return 'rgb(255, 205, 86)';  // Yellow (Suboptimal)
                        }} else if (value > 2000) {{
                            return 'rgb(255, 99, 132)';  // Red (Bad)
                        }} else {{
                            return 'rgb(75, 192, 192)';  // Default Green
                        }}
                    }}

                    const rco2Ctx = document.getElementById('rco2Chart').getContext('2d');
                    new Chart(rco2Ctx, {{
                        type: 'line',
                        data: {{
                            labels: data.timestamps,
                            datasets: [{{
                                label: 'RCO2',
                                data: data.rco2,
                                borderColor: data.rco2.map(getRCO2LineColor),
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
                            }},
                            plugins: {{
                                annotation: {{
                                    annotations: {{
                                        line1: {{
                                            type: 'line',
                                            yMin: 400,
                                            yMax: 400,
                                            borderColor: 'rgb(75, 192, 192)',
                                            borderWidth: 2,
                                            label: {{
                                                content: 'Good (400-1000)',
                                                enabled: true,
                                                position: 'center',
                                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                                font: {{
                                                    size: 12
                                                }}
                                            }}
                                        }},
                                        line2: {{
                                            type: 'line',
                                            yMin: 1000,
                                            yMax: 1000,
                                            borderColor: 'rgb(255, 205, 86)',
                                            borderWidth: 2,
                                            label: {{
                                                content: 'Suboptimal (1000-2000)',
                                                enabled: true,
                                                position: 'center',
                                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                                font: {{
                                                    size: 12
                                                }}
                                            }}
                                        }},
                                        line3: {{
                                            type: 'line',
                                            yMin: 2000,
                                            yMax: 2000,
                                            borderColor: 'rgb(255, 99, 132)',
                                            borderWidth: 2,
                                            label: {{
                                                content: 'Bad (>2000)',
                                                enabled: true,
                                                position: 'center',
                                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                                font: {{
                                                    size: 12
                                                }}
                                            }}
                                        }}
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
                                borderColor: data.atmp.map(getLineColor),
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
                            }},
                            plugins: {{
                                annotation: {{
                                    annotations: {{
                                        line: {{
                                            type: 'line',
                                            yMin: 100,
                                            yMax: 100,
                                            borderColor: 'rgb(0, 0, 0)',
                                            borderWidth: 2,
                                            label: {{
                                                content: 'Value 100',
                                                enabled: true,
                                                position: 'center',
                                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                                font: {{
                                                    size: 12
                                                }}
                                            }}
                                        }}
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
                                borderColor: data.rhum.map(getLineColor),
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
                            }},
                            plugins: {{
                                annotation: {{
                                    annotations: {{
                                        line: {{
                                            type: 'line',
                                            yMin: 100,
                                            yMax: 100,
                                            borderColor: 'rgb(0, 0, 0)',
                                            borderWidth: 2,
                                            label: {{
                                                content: 'Value 100',
                                                enabled: true,
                                                position: 'center',
                                                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                                font: {{
                                                    size: 12
                                                }}
                                            }}
                                        }}
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
