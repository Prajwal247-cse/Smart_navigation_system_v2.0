"""
backend/main.py — IntentRoute v2
=================================
Database  : PostgreSQL (via psycopg2)
ENV       : Reads DATABASE_URL from .env file automatically
STT       : Browser Web Speech API only (no audio file upload)

HOW TO SET UP:
  1. Install PostgreSQL from https://www.postgresql.org/download/windows
  2. Open pgAdmin → Create a database called: intentroute
  3. Create a .env file in the project root with:
        DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/intentroute
     (encode special chars: # → %23,  $ → %24,  @ → %40)
  4. pip install -r requirements.txt
  5. python model/train_model.py
  6. uvicorn backend.main:app --reload --port 8000
"""

import os, sys, math, pickle, hashlib, secrets
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

# ── Auto-load .env file ───────────────────────────────────────────────────────
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, '..')
load_dotenv(os.path.join(ROOT_DIR, '.env'))
# ─────────────────────────────────────────────────────────────────────────────

sys.path.append(ROOT_DIR)

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from utils.preprocessing import preprocess_text

MODEL_PATH = os.path.join(ROOT_DIR, 'model', 'intent_model.pkl')

# ── Load ML model ─────────────────────────────────────────────────────────────
if not os.path.exists(MODEL_PATH):
    raise RuntimeError("Model not found. Run: python model/train_model.py")
with open(MODEL_PATH, 'rb') as f:
    MODEL = pickle.load(f)

# ── Read DATABASE_URL ─────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "\n\n❌ DATABASE_URL not found!\n"
        "Create a .env file in your project root with:\n"
        "  DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/intentroute\n"
        "  (Special chars: # → %23   $ → %24   @ → %40)\n"
    )

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="IntentRoute v2 API",
    description="From Intention to Destination — PostgreSQL",
    version="2.0.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── PostgreSQL connection ─────────────────────────────────────────────────────
@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ── Init DB tables on startup ─────────────────────────────────────────────────
def init_db():
    sql_path = os.path.join(ROOT_DIR, 'database', 'db_setup.sql')
    with get_db() as conn:
        with conn.cursor() as cur:
            with open(sql_path) as f:
                cur.execute(f.read())
    print("[DB] PostgreSQL tables initialised ✓")

@app.on_event("startup")
def startup():
    try:
        init_db()
        print("[DB] Connected to PostgreSQL ✓")
    except Exception as e:
        print(f"[DB] Warning: {e}")

# ── Auth helpers ──────────────────────────────────────────────────────────────
_tokens: dict[str, int] = {}

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def make_token(user_id: int) -> str:
    token = secrets.token_hex(32)
    _tokens[token] = user_id
    return token

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization[7:]
    user_id = _tokens.get(token)
    if not user_id:
        raise HTTPException(401, "Invalid or expired token. Please log in again.")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(401, "User not found")
    return dict(row)

# ── Schemas ───────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    name:     str = Field(..., min_length=2)
    email:    str = Field(...)
    password: str = Field(..., min_length=6)

class LoginRequest(BaseModel):
    email:    str
    password: str

class NavigationRequest(BaseModel):
    query:      str             = Field(..., min_length=2)
    user_lat:   Optional[float] = None
    user_lon:   Optional[float] = None
    input_mode: str             = "text"

class ProfileUpdate(BaseModel):
    name:   Optional[str] = None
    avatar: Optional[str] = None

# ── Geo / time helpers ────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(p1) * math.cos(p2)
         * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)

def is_open(o, c):
    if o == '00:00' and c == '23:59':
        return True
    return o <= datetime.now().strftime('%H:%M') <= c

def enrich(row, ulat=None, ulon=None):
    d = dict(row)
    d['is_open'] = is_open(d['opening_time'], d['closing_time'])
    if ulat is not None:
        d['distance_m'] = haversine(ulat, ulon, d['latitude'], d['longitude'])
        d['maps_link']  = f"https://www.google.com/maps/dir/{ulat},{ulon}/{d['latitude']},{d['longitude']}"
    else:
        d['distance_m'] = None
        d['maps_link']  = f"https://www.google.com/maps/search/?api=1&query={d['latitude']},{d['longitude']}"
    return d

# ── Intent classification ─────────────────────────────────────────────────────
def classify(query):
    clean  = preprocess_text(query)
    intent = MODEL.predict([clean])[0]
    conf   = round(float(max(MODEL.predict_proba([clean])[0])) * 100, 1)
    return intent, conf

# ── Recommendation ────────────────────────────────────────────────────────────
def recommend(intent, ulat=None, ulon=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM facilities WHERE category=%s", (intent,))
            rows = cur.fetchall()
    if not rows:
        return None, []
    items = [enrich(r, ulat, ulon) for r in rows]
    items.sort(key=lambda f: (0 if f['is_open'] else 1, f['distance_m'] or 999_999))
    return items[0], items[1:]

# ── Core navigate logic ───────────────────────────────────────────────────────
def _do_navigate(query, mode, ulat, ulon, user):
    intent, conf = classify(query)
    best, alts   = recommend(intent, ulat, ulon)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO search_history(user_id,query,input_mode,intent,facility_name) VALUES(%s,%s,%s,%s,%s)",
                (user['id'], query, mode, intent, best['name'] if best else None)
            )

    if not best:
        return {
            "query": query, "input_mode": mode,
            "intent": intent, "confidence": conf,
            "recommended": None, "alternatives": [],
            "message": f"No facilities found for '{intent}'"
        }

    dist = f", {best['distance_m']}m away" if best['distance_m'] else ""
    st   = "open ✓" if best['is_open'] else "closed ✗"
    return {
        "query": query, "input_mode": mode,
        "intent": intent, "confidence": conf,
        "recommended": best, "alternatives": alts,
        "message": f"Found {len(alts)+1} {intent} places. Best: '{best['name']}' — {st}{dist}."
    }

# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/auth/signup")
def signup(req: SignupRequest):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (req.email.lower(),))
            if cur.fetchone():
                raise HTTPException(409, "Email already registered")
            cur.execute(
                "INSERT INTO users(name,email,password_hash) VALUES(%s,%s,%s) RETURNING id",
                (req.name, req.email.lower(), hash_password(req.password))
            )
            uid = cur.fetchone()['id']
            cur.execute("SELECT id,name,email,avatar,created_at FROM users WHERE id=%s", (uid,))
            user = dict(cur.fetchone())
    token = make_token(uid)
    return {"token": token, "user": user}

@app.post("/auth/login")
def login(req: LoginRequest):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email=%s", (req.email.lower(),))
            row = cur.fetchone()
    if not row or row['password_hash'] != hash_password(req.password):
        raise HTTPException(401, "Invalid email or password")
    token = make_token(row['id'])
    return {"token": token, "user": {
        "id": row['id'], "name": row['name'], "email": row['email'],
        "avatar": row['avatar'], "created_at": str(row['created_at'])
    }}

@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    return {k: v for k, v in user.items() if k != 'password_hash'}

# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/navigate")
def navigate(req: NavigationRequest, user=Depends(get_current_user)):
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    mode = req.input_mode if req.input_mode in ("text", "voice") else "text"
    return _do_navigate(req.query, mode, req.user_lat, req.user_lon, user)

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/history")
def get_history(user=Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM search_history WHERE user_id=%s ORDER BY searched_at DESC LIMIT 50",
                (user['id'],)
            )
            rows = cur.fetchall()
    return [dict(r) for r in rows]

@app.delete("/history/{hid}")
def delete_history(hid: int, user=Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM search_history WHERE id=%s AND user_id=%s", (hid, user['id']))
    return {"deleted": hid}

@app.delete("/history")
def clear_history(user=Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM search_history WHERE user_id=%s", (user['id'],))
    return {"message": "History cleared"}

# ═══════════════════════════════════════════════════════════════════════════════
# FAVOURITES
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/favourites")
def get_favs(user=Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.*, fav.added_at AS fav_added
                FROM facilities f
                JOIN favourites fav ON fav.facility_id = f.id
                WHERE fav.user_id = %s
                ORDER BY fav.added_at DESC
            """, (user['id'],))
            rows = cur.fetchall()
    return [enrich(r) for r in rows]

@app.post("/favourites/{fid}")
def add_fav(fid: int, user=Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO favourites(user_id,facility_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                (user['id'], fid)
            )
    return {"message": "Added to favourites"}

@app.delete("/favourites/{fid}")
def remove_fav(fid: int, user=Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM favourites WHERE user_id=%s AND facility_id=%s",
                (user['id'], fid)
            )
    return {"message": "Removed from favourites"}

# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/profile")
def get_profile(user=Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM search_history WHERE user_id=%s", (user['id'],))
            hc = cur.fetchone()['c']
            cur.execute("SELECT COUNT(*) AS c FROM favourites WHERE user_id=%s", (user['id'],))
            fc = cur.fetchone()['c']
    return {
        **{k: v for k, v in user.items() if k != 'password_hash'},
        "history_count": hc,
        "favourites_count": fc
    }

@app.put("/profile")
def update_profile(req: ProfileUpdate, user=Depends(get_current_user)):
    fields, vals = [], []
    if req.name:   fields.append("name=%s");   vals.append(req.name)
    if req.avatar: fields.append("avatar=%s"); vals.append(req.avatar)
    if not fields:
        raise HTTPException(400, "Nothing to update")
    vals.append(user['id'])
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE users SET {','.join(fields)} WHERE id=%s", vals)
            cur.execute(
                "SELECT id,name,email,avatar,created_at FROM users WHERE id=%s", (user['id'],)
            )
            updated = dict(cur.fetchone())
    return updated

# ═══════════════════════════════════════════════════════════════════════════════
# MISC
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/facilities")
def list_facilities(category: Optional[str] = None):
    with get_db() as conn:
        with conn.cursor() as cur:
            if category:
                cur.execute("SELECT * FROM facilities WHERE category=%s", (category.upper(),))
            else:
                cur.execute("SELECT * FROM facilities")
            rows = cur.fetchall()
    return [enrich(r) for r in rows]

@app.get("/health")
def health():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {"status": "ok", "version": "2.0.0", "database": "postgresql", "db_status": db_status}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
