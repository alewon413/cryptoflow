import requests
import psycopg2
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "cryptoflow",
    "user": "postgres",
    "password": "Zander123!"
}

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 20,
    "page": 1,
    "sparkline": False
}

def fetch_coins():
    logging.info("Fetching top 20 coins from CoinGecko...")
    response = requests.get(COINGECKO_URL, params=PARAMS)
    response.raise_for_status()
    return response.json()

def insert_data(coins):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    timestamp = datetime.now(timezone.utc)
    inserted = 0

    for coin in coins:
        # Upsert coin metadata
        cur.execute("""
            INSERT INTO coins (id, name, symbol, market_cap_rank)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET market_cap_rank = EXCLUDED.market_cap_rank
        """, (coin["id"], coin["name"], coin["symbol"], coin["market_cap_rank"]))

        # Insert current price as OHLCV (current price used for all since markets endpoint doesn't give OHLCV)
        price = coin["current_price"]
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
    logging.info(f"Done — {inserted} coins processed.")

if __name__ == "__main__":
    coins = fetch_coins()
    insert_data(coins)