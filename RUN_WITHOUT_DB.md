# Run the API Without Docker, PostgreSQL, or API Keys

Use **demo mode** to run the Climate Burden Index API with only Python and a virtual environment. No Docker, no PostgreSQL, and no API keys are required. Endpoints return sample data.

---

## 1. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
cd path\to\climate-exposure-system
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
cd climate-exposure-system
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your prompt.

---

## 2. Install dependencies

With the venv **activated**:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Turn on demo mode

Set the `DEMO_MODE` environment variable so the API does not try to connect to a database or load models.

**Windows (PowerShell):**
```powershell
$env:DEMO_MODE = "1"
```

**Windows (Command Prompt):**
```cmd
set DEMO_MODE=1
```

**macOS / Linux:**
```bash
export DEMO_MODE=1
```

---

## 4. Start the API

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

- **API:** http://localhost:8000  
- **Interactive docs:** http://localhost:8000/docs  
- **Health:** http://localhost:8000/health (will show `"demo_mode": true`)

---

## 5. Try the endpoints

All of these work in demo mode with **sample data** (no database or models):

**Score by latitude/longitude:**
```bash
curl "http://localhost:8000/score?lat=40.7128&lon=-74.0060"
curl "http://localhost:8000/score?lat=40.7128&lon=-74.0060&explain=true"
```

**Clusters (K-Means or HDBSCAN):**
```bash
curl "http://localhost:8000/clusters?method=kmeans"
curl "http://localhost:8000/clusters?method=hdbscan"
```

**NLP insights (already sample data, no API key):**
```bash
curl "http://localhost:8000/nlp-insights?geoid=36061001001"
```

---

## One-liner (after venv is created)

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1; $env:DEMO_MODE = "1"; uvicorn src.api.main:app --reload --port 8000
```

**macOS / Linux:**
```bash
source venv/bin/activate && export DEMO_MODE=1 && uvicorn src.api.main:app --reload --port 8000
```

---

## What demo mode does

| Item | With database | In demo mode |
|------|----------------|---------------|
| `/score` | Reverse-geocode + DB lookup | Sample CBI and percentile for any lat/lon |
| `/clusters` | Reads from DB | Returns 5 sample clusters |
| `/nlp-insights` | Could use LLM | Same placeholder text (no key needed) |
| `/health` | Checks DB/models | Reports `demo_mode: true`, no DB/model check |

When you have PostgreSQL (and optionally Docker) set up, run **without** `DEMO_MODE` (or set `DEMO_MODE=0`) to use the real database and models.
