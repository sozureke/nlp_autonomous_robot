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
python -m src.app.web_api
```

Open: [http://localhost:8000](http://localhost:8000)

## Run Next.js Web App

```bash
cd web
cp .env.local.example .env.local
npm install
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

By default Next.js uses `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.