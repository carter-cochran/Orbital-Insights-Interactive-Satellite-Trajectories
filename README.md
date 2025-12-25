# Orbital Insights: Interactive Satellite Trajectories

Minimal Route B project with a FastAPI backend that serves CZML from TLEs and a CesiumJS frontend that animates satellites on a 3D globe.

## Requirements
- Python 3.11+
- Network access to CelesTrak (for TLE refresh)

## Backend setup (port 8000)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Run backend in the background
```bash
nohup uvicorn app.main:app --reload --port 8000 > backend.log 2>&1 &
```

### Check backend health
```bash
curl http://localhost:8000/api/health
```

## Frontend setup (port 8080)
```bash
cd frontend
python3 -m http.server 8080
```
Then open `http://localhost:8080` in your browser.

Note: the dev server is HTTP only. There is no HTTPS endpoint unless you add an HTTPS-capable static server.

## END LEFTOVER BACKGROUND PROCESSES
```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
kill {process}
```

## Cesium Ion token
- Keep the quotes when you paste your token into `frontend/config.js`.
- Example:
  ```js
  window.CESIUM_ION_TOKEN = "YOUR_TOKEN_HERE";
  ```

## API endpoints
- `GET /api/health` -> `{ "status": "ok", "last_refresh_utc": "...", "count": N }`
- `GET /api/satellites?limit=200` -> list of `{ norad_id, name }`
- `GET /api/czml?ids=25544,20580&minutes=90&step=10` -> `{ czml, used, skipped }`

## Troubleshooting
- **CORS errors**: the backend allows `http://localhost:8080` and `http://127.0.0.1:8080`. Use one of those exact origins.
- **TLE refresh**: the backend caches TLEs for 6 hours. Restart the server or wait for refresh if CelesTrak data looks stale.
- **ISS altitude sanity check**: when loading NORAD ID `25544`, the altitude should be around 400,000 meters in the Cesium inspector or by checking CZML heights.
- **No imagery**: if the globe is blank, check network access to `https://a.tile.openstreetmap.org/`.

## Project structure
- `app/main.py`: FastAPI app and endpoints
- `app/tle_cache.py`: TLE fetch + cache logic
- `frontend/index.html`: Cesium viewer UI
- `frontend/main.js`: Fetch CZML and load into Cesium
