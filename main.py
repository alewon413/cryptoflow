from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Optional

app = FastAPI(title="CryptoFlow API")

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "cryptoflow",
    "user": "postgres",
    "password": "Zander123!"
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)


@app.get("/coins")
def get_coins():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM coins ORDER BY market_cap_rank")
    coins = cur.fetchall()
    cur.close()
    conn.close()
    return list(coins)


@app.get("/prices")
def get_prices(
    coin: str = Query(..., description="Coin ID e.g. bitcoin"),
    limit: int = Query(50, description="Number of rows to return")
):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT coin_id, timestamp, open, high, low, close, volume
        FROM prices
        WHERE coin_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """, (coin, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for coin: {coin}")
    return list(rows)


@app.get("/stats")
def get_stats(coin: str = Query(..., description="Coin ID e.g. bitcoin")):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            coin_id,
            ROUND(AVG(close)::numeric, 2) AS avg_close,
            ROUND(MAX(high)::numeric, 2)  AS max_high,
            ROUND(MIN(low)::numeric, 2)   AS min_low,
            ROUND(SUM(volume)::numeric, 2) AS total_volume,
            COUNT(*) AS data_points
        FROM prices
        WHERE coin_id = %s
        GROUP BY coin_id
    """, (coin,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"No data found for coin: {coin}")
    return dict(row)


@app.post("/ingest")
def trigger_ingest():
    import subprocess
    import sys
    result