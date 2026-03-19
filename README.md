# IntentRoute v2 🧭
### *From Intention to Destination.*

> A Semantic Intent-Based, Context-Aware Smart Campus Navigation System with authentication, voice input, search history, favourites, profile management, and dark/light theme switching.

---

## ✨ Features

- 🔐 **Login & Signup** — Email + password authentication with secure SHA-256 hashing
- 📍 **Location Popup** — Asks for GPS on first login to calculate distances
- 🔤 **Text Query** — Type natural language queries like *"I need a quiet place to study"*
- 🎙 **Voice Input** — Speak your query via browser microphone (Web Speech API)
- 🤖 **Hello Nav** — Always-listening voice agent, say *"Hello Nav I need food"* to auto-navigate
- 🏫 **Smart Recommendations** — Filtered by intent, open status and distance
- 🗺 **Google Maps** — Direct navigation link to recommended facility
- 🕐 **Search History** — Every search saved per user, replayable with one click
- ❤️ **Favourites** — Save and revisit campus locations
- 👤 **Profile Page** — Edit name, choose avatar, see usage stats
- 🌙☀️ **Dark / Light Theme** — Toggle with one click, preference saved
- 🎨 **Animated UI** — Floating orbs, particles, shimmer effects, staggered animations

---

## 🗂 Project Structure

```
intentroute-v2/
├── .env.example              ← copy to .env and add your DB password
├── .env                      ← YOU CREATE THIS (not in zip)
├── Procfile                  ← for Render deployment
├── runtime.txt               ← Python version for Render
├── requirements.txt          ← Python dependencies
│
├── backend/
│   └── main.py               ← FastAPI backend (PostgreSQL)
│
├── database/
│   └── db_setup.sql          ← PostgreSQL schema + seed data
│
├── dataset/
│   └── intents.csv           ← 180 labelled training queries
│
├── model/
│   ├── train_model.py        ← TF-IDF + Logistic Regression training
│   └── intent_model.pkl      ← saved model (generated after training)
│
├── frontend/
│   └── index.html            ← complete single-page UI
│
└── utils/
    └── preprocessing.py      ← NLP pipeline (NLTK fallback built-in)
```

---

## 🧠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | PostgreSQL (psycopg2-binary) |
| ML Model | Scikit-learn — TF-IDF + Logistic Regression |
| NLP | NLTK (with built-in fallback) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Voice (Browser) | Web Speech API |
| Maps | Google Maps Directions URL |
| Auth | SHA-256 password hashing + token-based sessions |
| Config | python-dotenv (.env file) |

---

## 🎯 Supported Intents

| Intent | Example Queries |
|---|---|
| `STUDY` | *"I want a quiet place to study"*, *"Where is the library?"* |
| `FOOD` | *"Where can I eat?"*, *"I'm hungry"*, *"Find me a canteen"* |
| `MEDICAL` | *"I need a doctor"*, *"Where is the clinic?"*, *"I feel sick"* |
| `ADMIN` | *"Where is the registrar?"*, *"I need my transcript"* |
| `LAB` | *"Where is the computer lab?"*, *"I need to use MATLAB"* |
| `HOSTEL` | *"Where is my hostel?"*, *"I locked myself out of my room"* |

---

## 🚀 How to Run Locally (Windows)

### Prerequisites
- Python 3.11 → [python.org](https://python.org) *(check "Add to PATH" during install)*
- PostgreSQL 16 → [postgresql.org/download/windows](https://postgresql.org/download/windows)

---

### Step 1 — Extract the zip

Unzip `intentroute-v2.zip` to a folder, for example:
```
E:\intentroute-v2\
```

---

### Step 2 — Create the PostgreSQL database

Open **pgAdmin 4** from Start Menu:
1. Expand **Servers → PostgreSQL 16**
2. Enter your postgres password when prompted
3. Right-click **Databases → Create → Database**
4. Name it: `intentroute`
5. Click **Save**

---

### Step 3 — Create the `.env` file

In your project folder `E:\intentroute-v2\`, create a file called `.env` *(no extension)* with this content:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/intentroute
```

**If your password has special characters, encode them:**

| Character | Encoded |
|---|---|
| `#` | `%23` |
| `$` | `%24` |
| `@` | `%40` |
| `!` | `%21` |

Example — password `pzqm123#$` becomes:
```
DATABASE_URL=postgresql://postgres:pzqm123%23%24@localhost:5432/intentroute
```

---

### Step 4 — Install dependencies

Open **Command Prompt**, navigate to your project folder and run:

```cmd
cd E:\intentroute-v2
pip install -r requirements.txt
```

If `pip` is not found:
```cmd
python -m pip install -r requirements.txt
```

---

### Step 5 — Train the ML model

```cmd
python model/train_model.py
```

Expected output:
```
[1/5] Loading dataset... Loaded 180 samples across 6 intents.
[2/5] Preprocessing text with NLTK...
[3/5] Splitting into train/test (80/20)...
[4/5] Training TF-IDF + Logistic Regression pipeline...
[5/5] Accuracy: ~69%
Model saved → model/intent_model.pkl ✓
```

> ⚠️ Always retrain on your machine. Never use the pre-built `.pkl` from the zip — it was built on a different sklearn version and will cause errors.

---

### Step 6 — Start the backend

```cmd
uvicorn backend.main:app --reload --port 8000
```

Expected output:
```
[DB] PostgreSQL tables initialised ✓
[DB] Connected to PostgreSQL ✓
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

### Step 7 — Open the frontend

Double-click `frontend/index.html` — it opens in your browser.

---

### Step 8 — Create a shortcut (optional)

Create a file called `run.bat` in your project root:

```bat
@echo off
cd /d E:\intentroute-v2
uvicorn backend.main:app --reload --port 8000
pause
```

Double-click `run.bat` every time you want to start the server.

---

## ✅ Verify It's Working

Open your browser and go to:
```
http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "2.0.0",
  "database": "postgresql",
  "db_status": "connected"
}
```

Interactive API docs:
```
http://localhost:8000/docs
```

---

## 🔌 API Reference

### Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/login` | Login and get token |
| GET | `/auth/me` | Get current user info |

### Navigation

| Method | Endpoint | Description |
|---|---|---|
| POST | `/navigate` | Text or voice query → recommend facility |

### User Data

| Method | Endpoint | Description |
|---|---|---|
| GET | `/history` | Get search history |
| DELETE | `/history/{id}` | Delete one history item |
| DELETE | `/history` | Clear all history |
| GET | `/favourites` | Get saved favourites |
| POST | `/favourites/{id}` | Add to favourites |
| DELETE | `/favourites/{id}` | Remove from favourites |
| GET | `/profile` | Get profile + stats |
| PUT | `/profile` | Update name / avatar |

### Campus

| Method | Endpoint | Description |
|---|---|---|
| GET | `/facilities` | List all facilities |
| GET | `/health` | Server + DB status |

---

### Example Request

```json
POST /navigate
{
  "query": "I need a quiet place to study",
  "user_lat": 3.1380,
  "user_lon": 101.6860,
  "input_mode": "text"
}
```

### Example Response

```json
{
  "query": "I need a quiet place to study",
  "input_mode": "text",
  "intent": "STUDY",
  "confidence": 89.9,
  "recommended": {
    "name": "24-Hour Study Hall",
    "building": "Student Hub",
    "floor": "Ground Floor",
    "is_open": true,
    "distance_m": 22.2,
    "maps_link": "https://www.google.com/maps/dir/..."
  },
  "alternatives": [ ... ],
  "message": "Found 5 STUDY places. Best: '24-Hour Study Hall' — open ✓, 22.2m away."
}
```

---

## ❗ Common Errors & Fixes

| Error | Fix |
|---|---|
| `No such file: train_model.py` | Check spelling — it's `train_model.py` not `train_moddel.py` |
| `NotFittedError: idf vector is not fitted` | Retrain: `python model/train_model.py` |
| `DATABASE_URL not found` | Make sure `.env` file exists in project root |
| `password authentication failed` | Check your PostgreSQL password in `.env` |
| `could not connect to server` | PostgreSQL service is not running — open Services → start `postgresql-x64-16` |
| `No module named 'psycopg2'` | Run `pip install psycopg2-binary` |
| `No module named 'fastapi'` | Run `pip install -r requirements.txt` |
| `No named backend` | You're in the wrong folder — run `cd E:\intentroute-v2` first |
| Mic not working | Use Chrome or Edge — Firefox doesn't support Web Speech API |
| CORS error in browser | Make sure backend is running on port 8000 |

---

## 🚢 Deploying to Render

1. Push project to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add a **PostgreSQL database** in Render → copy the **Internal Database URL**
6. Add environment variable: `DATABASE_URL` = *(paste the URL from step 5)*
7. Deploy — Render handles everything automatically

---

## 📊 Model Details

| Metric | Value |
|---|---|
| Training samples | 180 (30 × 6 intents) |
| Algorithm | TF-IDF (unigrams + bigrams) + Logistic Regression |
| Test accuracy | ~69% |
| Intents | STUDY, FOOD, MEDICAL, ADMIN, LAB, HOSTEL |

> Accuracy improves with more training data. Add more examples to `dataset/intents.csv` and retrain.

---

*IntentRoute v2 — From Intention to Destination.*
