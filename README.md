## Setup

```bash
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run CLI

```bash
python -m src.app.main
```

## Run Web UI (FastAPI)

```bash
export PYTHONPATH="$PWD"
export WEB_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
python -m src.app.web_api
```

Remote clients: set `WEB_CORS_ORIGINS` to include your PC’s Next.js origin, e.g. `http://192.168.1.50:3000`.

Open: [http://localhost:8000](http://localhost:8000) (or `http://<pi-ip>:8000` from LAN)

API notes:
- `POST /api/plan` and `POST /api/execute` accept `{ "command": "...", "mode": "llm|rules|direct" }`.
- Plan steps can contain optional `duration` (seconds) and `repeat` fields.
- Metrics endpoints: `GET /api/metrics`, `POST /api/metrics/reset`.

## Run Next.js Web App

```bash
cd web
cp .env.local.example .env.local
npm install
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

By default Next.js uses `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

## Live Metrics Logger

```bash
python experiment/live_metrics_logger.py --base-url http://localhost:8000
```

This writes session artifacts into `experiment/results/live_session_<timestamp>/`.