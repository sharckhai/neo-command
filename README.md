# VirtueCommand

VirtueCommand is a chat-driven healthcare intelligence system for NGO mission planners. It turns messy facility data into verified, geocoded, and searchable intelligence, then presents it through a map-first conversational UI.

## What’s Included
- **Data pipeline** (`src/pipeline`) that cleans, geocodes, fingerprints, embeds, and uploads facility data.
- **Backend** (`src/server`) that provides SSE chat streaming, facility endpoints, and agent logic (Explore / Verify / Plan).
- **Frontend** (`apps/web`) built with Next.js and Mapbox for the two-panel map + chat experience.

## Quick Start
1. Set up environment variables (see `docs/SETUP.md`).
2. Run the pipeline to generate `output/step4_entities.parquet` + `output/step4_embeddings.parquet`.
3. Start the backend and frontend.

See `docs/SETUP.md` for full instructions.
