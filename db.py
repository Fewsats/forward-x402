import apsw
import datetime as dt
from pathlib import Path
import os
import base64
import shutil
from fastmigrate.core import create_db, run_migrations
from fastcore.all import dict2obj

import apsw.bestpractice

apsw.bestpractice.apply(apsw.bestpractice.recommended)

# Determine database path based on environment
if not os.environ.get("RAILWAY_PROJECT_NAME"): db_path = Path("data/foward-x402.db")
else: db_path = Path("/data/foward-x402.db")


db_path.parent.mkdir(parents=True, exist_ok=True)    
migrations_dir = "migrations"

# Init DB
# Create/verify there is a versioned database, or else fail
current_version = create_db(db_path)
print(f"DB: {current_version=}")

success = run_migrations(db_path, migrations_dir, verbose=False)
if not success: raise Exception("Database migration failed!")

conn= apsw.Connection(str(db_path))

def ensure_user(user_id, email, name, picture):
    cur = conn.cursor()
    print(f"Ensuring user {user_id} {email} {name} {picture}")
    cur.execute("INSERT OR IGNORE INTO users (id, email, name, picture) VALUES (?, ?, ?, ?)",
                (user_id, email, name, picture))
    return cur.getconnection().last_insert_rowid()

def get_user(user_id):
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, picture FROM users WHERE id = ?", (user_id,))
    id, email, name, picture = cur.fetchone()
    return dict2obj({"id": id, "email": email, "name": name, "picture": picture})


def create_email_endpoint(user_id, email, label, base_price):
    """Create a new email endpoint"""
    import uuid
    import secrets
    cur = conn.cursor()
    endpoint_id = str(uuid.uuid4())
    short_url = secrets.token_urlsafe(8)
    cur.execute("""
        INSERT INTO email_endpoints (id, user_id, email, label, short_url, base_price)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (endpoint_id, user_id, email, label, short_url, base_price * 1000000))
    return endpoint_id

def list_endpoints_by_user(user_id):
    """List all endpoints for a user"""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, email, label, short_url, base_price, is_active, hit_count, payment_count, created_at
        FROM email_endpoints WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    return [dict2obj({
        "id": row[0],
        "user_id": row[1],
        "email": row[2],
        "label": row[3],
        "short_url": row[4],
        "base_price": row[5] / 1000000,
        "is_active": row[6],
        "hit_count": row[7],
        "payment_count": row[8],
        "created_at": row[9]
    }) for row in cur.fetchall()]

def get_endpoint_by_short_url(short_url):
    """Get endpoint by short URL"""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, email, label, short_url, base_price, is_active, hit_count, payment_count, created_at
        FROM email_endpoints WHERE short_url = ? AND is_active = TRUE
    """, (short_url,))
    row = cur.fetchone()
    if not row: return None
    return dict2obj({
        "id": row[0],
        "user_id": row[1],
        "email": row[2],
        "label": row[3],
        "short_url": row[4],
        "base_price": row[5] / 1000000,
        "is_active": row[6],
        "hit_count": row[7],
        "payment_count": row[8],
        "created_at": row[9]
    })

def update_hit_count(endpoint_id):
    """Update hit_count for an endpoint"""
    cur = conn.cursor()
    cur.execute("""
        UPDATE email_endpoints 
        SET hit_count = hit_count + 1
        WHERE id = ?
    """, (endpoint_id,))

def update_pay_count(endpoint_id):
    """Update payment_count for an endpoint"""
    cur = conn.cursor()
    cur.execute("""
        UPDATE email_endpoints 
        SET payment_count = payment_count + 1
        WHERE id = ?
    """, (endpoint_id,))