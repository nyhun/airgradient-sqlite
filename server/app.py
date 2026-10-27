import atexit
import calendar
import sqlite3
import threading
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "logs.db"

# Readings arrive every ~30s. To spare the SD card, inserts are committed in
# batches instead of one transaction (and fsync) per reading.
COMMIT_INTERVAL = 300  # seconds
MAX_POINTS = 1500      # upper bound of points returned by /data

METRICS = ("pm02", "rco2", "atmp", "rhum")
AGGS = {"avg": "AVG", "min": "MIN", "max": "MAX"}

_lock = threading.Lock()
_last_commit = time.monotonic()

_db = sqlite3.connect(DB_PATH, check_same_thread=False)
_db.execute("PRAGMA journal_mode=WAL")
_db.execute("PRAGMA synchronous=NORMAL")
_db.execute("PRAGMA cache_size=-2000")
_db.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pm02 INTEGER,
    rco2 INTEGER,
    atmp FLOAT,
    rhum INTEGER,
    timestamp TEXT
)''')
_db.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
_db.commit()


def _flush():
    with _lock:
        _db.commit()


atexit.register(_flush)


class Log(BaseModel):
    wifi: int
    pm02: int
    rco2: int
    atmp: float
    rhum: int


@app.post("/log")
def log_number(log: Log):
    global _last_commit
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with _lock:
        _db.execute(
            "INSERT INTO logs (pm02, rco2, atmp, rhum, timestamp) VALUES (?, ?, ?, ?, ?)",
            (log.pm02, log.rco2, log.atmp, log.rhum, timestamp))
        if time.monotonic() - _last_commit >= COMMIT_INTERVAL:
            _db.commit()
            _last_commit = time.monotonic()
    return {"message": "Values logged successfully!"}


def _wall_epoch(dt: datetime) -> int:
    """Local wall-clock time encoded as if it were UTC (matches SQLite's strftime('%s'))."""
    return calendar.timegm(dt.timetuple())


@app.get("/data")
def get_data(last: int = 86400, start: int = 0, end: int = 0, step: int = 0, agg: str = "avg"):
    """Return bucketed series. Times are wall-clock-as-UTC epoch seconds.

    last: seconds back from now (used when start/end are not given)
    step: bucket size in seconds, 0 = automatic
    agg:  avg | min | max
    """
    if agg not in AGGS:
        raise HTTPException(422, f"agg must be one of {sorted(AGGS)}")
    now = _wall_epoch(datetime.now())
    if not end:
        end = now
    if not start:
        start = end - max(last, 60)
    if start >= end:
        raise HTTPException(422, "start must be before end")
    if step <= 0:
        step = max(30, -(-(end - start) // 600))
        # snap to a "nice" bucket size
        for nice in (30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 14400, 21600, 43200, 86400):
            if step <= nice:
                step = nice
                break
    if (end - start) // step > MAX_POINTS:
        step = -(-(end - start) // MAX_POINTS)

    fn = AGGS[agg]
    cols = ", ".join(f"{fn}({m})" for m in METRICS)
    with _lock:
        rows = _db.execute(
            f"SELECT CAST(strftime('%s', timestamp) AS INTEGER) / ? * ? AS b, {cols} "
            "FROM logs WHERE timestamp >= datetime(?, 'unixepoch') AND timestamp < datetime(?, 'unixepoch') "
            "GROUP BY b ORDER BY b",
            (step, step, start, end)).fetchall()

    out = {"now": now, "start": start, "end": end, "step": step, "t": [r[0] for r in rows]}
    for i, m in enumerate(METRICS, 1):
        out[m] = [None if r[i] is None else round(r[i], 2) for r in rows]
    return out


@app.get("/", response_class=HTMLResponse)
def get_chart(request: Request):
    return templates.TemplateResponse("chart_template.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    # access_log off: no per-request log lines written to the SD card
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False, log_level="warning")
