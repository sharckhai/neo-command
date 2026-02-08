# VirtueCommand Setup

## Requirements
- Python 3.12+
- Node.js 20+
- Mapbox token (for map rendering)
- OpenAI API key (for LLM steps and embeddings)

## Environment Variables
Create a `.env` at the repo root with:
```
OPENAI_API_KEY=...
PIPELINE_TARGET=local
MAPBOX_TOKEN=...                # backend uses this for diagnostics only
NEXT_PUBLIC_MAPBOX_TOKEN=...    # frontend uses this for Mapbox
```

Optional:
```
PIPELINE_GEO_FETCH=1
ENTITIES_PARQUET=output/step4_entities.parquet
EMBEDDINGS_PARQUET=output/step4_embeddings.parquet
LANCEDB_PATH=output/lancedb
```

## Data Pipeline
Run each step from the repo root:
```
uv sync
uv run pipeline clean
uv run pipeline geocode
uv run pipeline fingerprint
uv run pipeline embed
uv run pipeline upload
```

This produces:
- `output/step4_entities.parquet`
- `output/step4_embeddings.parquet`

## Backend
Run the FastAPI server:
```
uv run python -m uvicorn server.app:app --reload
```

Endpoints:
- `GET /api/health`
- `GET /api/facilities`
- `POST /api/chat` (SSE)

## Frontend
Install dependencies and run Next.js:
```
cd apps/web
npm install
npm run dev
```

The UI expects the backend at the same origin. If you run them on different ports, add a proxy or update fetch URLs in `apps/web/components/ChatPanel.tsx` and `apps/web/components/MapPanel.tsx`.

## Notes
- GraphRAG / Knowledge Graph is intentionally excluded.
- If `OPENAI_API_KEY` is missing, the backend will return fallback responses.
