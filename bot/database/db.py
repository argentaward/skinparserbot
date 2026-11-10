import aiosqlite
from typing import Optional, Dict, Any, List
from config import settings

INIT_DB_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    deposit_fee REAL DEFAULT 0.0,
    sale_fee REAL DEFAULT 5.0,
    withdraw_fee REAL DEFAULT 5.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    skin_name TEXT,
    donor_market TEXT,
    recipient_market TEXT,
    buy_price REAL,
    sell_price REAL,
    net_profit REAL,
    roi REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS market_prices (
    market_name TEXT,
    market_hash_name TEXT,
    price REAL,
    volume INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (market_name, market_hash_name)
);

CREATE INDEX IF NOT EXISTS idx_market_prices_hash ON market_prices(market_hash_name);
"""

async def init_db():
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.executescript(INIT_DB_SQL)
        await db.commit()

async def get_or_create_user(user_id: int, username: Optional[str] = None) -> Dict[str, Any]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            
        await db.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()
        
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row)

async def update_user_fees(user_id: int, deposit_fee: float, sale_fee: float, withdraw_fee: float):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET deposit_fee = ?, sale_fee = ?, withdraw_fee = ?
            WHERE user_id = ?
            """,
            (deposit_fee, sale_fee, withdraw_fee, user_id)
        )
        await db.commit()

async def add_deal(
    user_id: int,
    skin_name: str,
    donor_market: str,
    recipient_market: str,
    buy_price: float,
    sell_price: float,
    net_profit: float,
    roi: float
) -> int:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO deals (
                user_id, skin_name, donor_market, recipient_market,
                buy_price, sell_price, net_profit, roi
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, skin_name, donor_market, recipient_market, buy_price, sell_price, net_profit, roi)
        )
        await db.commit()
        return cursor.lastrowid

async def get_user_deals(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM deals WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def bulk_save_market_prices(market_name: str, items: List[tuple]):
    """
    items: list of (market_hash_name, price, volume)
    """
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.executemany(
            """
            INSERT INTO market_prices (market_name, market_hash_name, price, volume, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(market_name, market_hash_name) DO UPDATE SET
                price = excluded.price,
                volume = excluded.volume,
                updated_at = CURRENT_TIMESTAMP
            """,
            [(market_name, name, price, vol) for name, price, vol in items]
        )
        await db.commit()

async def find_market_item(market_hash_name: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM market_prices WHERE market_hash_name = ? COLLATE NOCASE",
            (market_hash_name,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def search_market_items(query: str, limit: int = 10) -> List[str]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute(
            """
            SELECT DISTINCT market_hash_name FROM market_prices
            WHERE market_hash_name LIKE ?
            ORDER BY volume DESC, price DESC
            LIMIT ?
            """,
            (f"%{query}%", limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_total_prices_count(market_name: str = "Market.CSGO") -> int:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM market_prices WHERE market_name = ?",
            (market_name,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
