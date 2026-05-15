import requests
import psycopg2
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 20,
    "page": 1,
    "sparkline": False
}


# -------------------------
# DB CONNECTION (Neon)
# -------------------------
def get_conn():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )


# -------------------------
# DISCORD ALERT
# -------------------------
def send_discord_alert(message: str):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logging.warning("No Discord webhook found.")
        return

    try:
        requests.post(webhook_url, json={"content": message})
    except Exception as e:
        logging.error(f"Discord alert failed: {e}")


# -------------------------
# FETCH DATA
# -------------------------
def fetch_coins():
    logging.info("Fetching top 20 coins from CoinGecko...")

    HEADERS = {
        "x-cg-demo-api-key": "CG-N6mZ7unYxXmcuGPFWndr6VBt",
        "User-Agent": "CryptoFlow/1.0"
    }

    response = requests.get(
        COINGECKO_URL,
        params=PARAMS,
        headers=HEADERS
    )

    logging.info(f"Status: {response.status_code}")
    response.raise_for_status()

    return response.json()


# -------------------------
# INSERT INTO DATABASE
# -------------------------
def insert_data(coins):
    conn = get_conn()
    cur = conn.cursor()

    timestamp = datetime.utcnow()
    inserted = 0

    for coin in coins:
        # coins table
        cur.execute("""
            INSERT INTO coins (id, name, symbol, market_cap_rank)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET market_cap_rank = EXCLUDED.market_cap_rank
        """, (
            coin["id"],
            coin["name"],
            coin["symbol"],
            coin["market_cap_rank"]
        ))

        price = coin["current_price"]

        # prices table
        cur.execute("""
            INSERT INTO prices (coin_id, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (coin_id, timestamp) DO NOTHING
        """, (
            coin["id"],
            timestamp,
            price,
            coin["high_24h"],
            coin["low_24h"],
            price,
            coin["total_volume"]
        ))

        inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    logging.info(f"Inserted {inserted} coins.")


    # -------------------------
    # DISCORD NOTIFICATION
    # -------------------------
    pst_time = datetime.now(
        ZoneInfo("America/Los_Angeles")
    ).strftime("%Y-%m-%d %I:%M:%S %p")

    send_discord_alert(
        f"🟢 CryptoFlow Ingestion Complete\n"
        f"Coins updated: {inserted}\n"
        f"PST Time: {pst_time}"
    )


# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    coins = fetch_coins()
    insert_data(coins)