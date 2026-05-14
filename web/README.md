### 1) Install dependencies

From the repository root:

```bash
cd web
yarn install # or npm install
```

(Yarn 1 / Classic matches `yarn.lock` and `packageManager` in `package.json`.)

### 2) Configure API URL

```bash
cp .env.local.example .env.local
```

In `.env.local`, uncomment **exactly one** of:

- `**ROBOT_API_REWRITE_TARGET=http://<host>:8000`** — proxy via Next (`/api/…`); typical for a Pi on the LAN.
- `**NEXT_PUBLIC_ROBOT_API_BASE=http://<host>:8000`** — browser talks to the API directly; requires CORS on the backend.

Do not set both. Restart `yarn dev` after edits.

### 3) Run frontend

```bash
yarn dev # or npm start dev
```

Open [http://localhost:3000](http://localhost:3000).

### 4) Run backend (on robot host / Raspberry Pi)

From repository root:

```bash
# export WEB_CORS_ORIGINS="http://localhost:3000,http://192.168.1.50:3000"
python -m src.app.web_api
```

### 5) Typical setup (Pi + laptop)

- Backend on Raspberry Pi: listen on `0.0.0.0:8000` (e.g. uvicorn `--host 0.0.0.0`).
- Frontend on the laptop: same Wi‑Fi as the Pi.
- `.env.local` on the laptop: prefer `**ROBOT_API_REWRITE_TARGET=http://<PI_IP>:8000**` (no CORS to the Pi), or `**NEXT_PUBLIC_ROBOT_API_BASE=…**` if you want direct calls and configure CORS.
- Pi firewall: allow TCP 8000 from LAN.
- FastAPI: `WEB_CORS_ORIGINS` must include `http://localhost:3000` only for **direct** (`NEXT_PUBLIC_ROBOT_API_BASE`) mode.

