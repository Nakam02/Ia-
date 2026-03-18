# database.py - Connexion MongoDB via Motor (async)
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Connexion avec paramètres SSL compatibles Python 3.13
client = motor.motor_asyncio.AsyncIOMotorClient(
    os.getenv("MONGO_URI"),
    tls=True,
    tlsAllowInvalidCertificates=False,
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
)

db = client["monbot"]

# ── Collections ───────────────────────────────────────────────────
sanctions_col    = db["sanctions"]
config_col       = db["config"]
blacklist_col    = db["blacklist"]
whitelist_col    = db["whitelist"]
badwords_col     = db["badwords"]
tempmute_col     = db["tempmutes"]
tempban_col      = db["tempbans"]
owners_col       = db["owners"]

# ── Helpers génériques ────────────────────────────────────────────
async def get_config(guild_id: int) -> dict:
    doc = await config_col.find_one({"guild_id": guild_id})
    return doc or {}

async def set_config(guild_id: int, data: dict):
    await config_col.update_one(
        {"guild_id": guild_id},
        {"$set": data},
        upsert=True
    )

async def add_sanction(guild_id: int, user_id: int, sanction: dict):
    await sanctions_col.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$push": {"sanctions": sanction}},
        upsert=True
    )

async def get_sanctions(guild_id: int, user_id: int) -> list:
    doc = await sanctions_col.find_one({"guild_id": guild_id, "user_id": user_id})
    return doc["sanctions"] if doc else []

async def clear_sanctions(guild_id: int, user_id: int):
    await sanctions_col.delete_one({"guild_id": guild_id, "user_id": user_id})

async def clear_all_sanctions(guild_id: int):
    await sanctions_col.delete_many({"guild_id": guild_id})
