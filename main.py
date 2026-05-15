from fastapi import FastAPI, Query, HTTPException
import psycopg2
import psycopg2.extras
import os

app = FastAPI(title="CryptoFlow API")


def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )


@app.get("/coins")
def get_coins():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM coins ORDER BY market_cap_rank")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return list(rows)


@app.get("/prices")
def get_prices(
    coin: str = Query(...),
    limit: int = Query(50)
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
        raise HTTPException(status_code=404, detail="No data found")

    return list(rows)


@app.get("/stats")
def get_stats(coin: str = Query(...)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            coin_id,
            ROUND(AVG(close)::numeric, 2) AS avg_close,
            ROUND(MAX(high)::numeric, 2) AS max_high,
            ROUND(MIN(low)::numeric, 2) AS min_low,
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
        raise HTTPException(status_code=404, detail="No data found")

    return dict(row)


# ✅ NEW: latest DB snapshot (your "live" replacement)
@app.get("/latest")
def get_latest():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT ON (coin_id)
            coin_id,
            timestamp,
            close,
            high,
            low,
            volume
        FROM prices
        ORDER BY coin_id, timestamp DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# ⚠️ optional true live endpoint (CoinGecko direct)
@app.get("/live/{coin}")
def live_price(coin: str):
    import requests

    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": coin, "vs_currencies": "usd"}
    )

    return r.json()