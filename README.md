# cricxJac

Starter FastAPI app to ingest ball-by-ball events, maintain match state, compute dominance/momentum metrics, and stream updates.

This scaffold supports a pluggable LiveFeedAdapter so you can connect to a provider (CricAPI, ESPN, ICC, or a webhook).

Quick start
-----------
- Copy `.env.example` to `.env` and set provider credentials if available.
- Start services with Docker Compose: `docker compose up --build`.
- POST events to `POST /events` or configure the adapter to pull/push live feed.

Endpoints
---------
- POST /events — ingest an event
- GET /matches/{match_id}/state — get current snapshot
- GET /matches/{match_id}/metrics — computed metrics
- WS /matches/{match_id}/stream — live updates

Notes
-----
This is a starter scaffold. Replace the `LiveFeedAdapter` with your provider's integration and add API keys in `.env."