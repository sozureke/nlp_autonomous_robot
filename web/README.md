## Next.js Web UI

This directory contains a standalone Next.js frontend for the robot FastAPI backend.

### 1) Install dependencies

```bash
cd web
npm install
```

### 2) Configure API URL

```bash
cp .env.local.example .env.local
```

Set `NEXT_PUBLIC_API_BASE_URL` to your FastAPI URL if it differs from `http://localhost:8000`.

### 3) Run frontend

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 4) Run backend (on robot host / Raspberry Pi)

From repository root:

```bash
# Allow your frontend origin(s), comma-separated:
# export WEB_CORS_ORIGINS="http://localhost:3000,http://192.168.1.50:3000"
python -m src.app.web_api
```

### 5) Typical "Option 1" setup (recommended)

- Backend + robot hardware run on Raspberry Pi.
- Frontend runs on your development computer.
- In `.env.local` on your computer, set:

```bash
NEXT_PUBLIC_API_BASE_URL=http://<RASPBERRY_PI_IP>:8000
```

- On Raspberry Pi, set `WEB_CORS_ORIGINS` to include your frontend origin.
