import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from pydantic import BaseModel
from .models import Event
from .engine import MatchStateManager
from .metrics import compute_metrics
from .ingest import SampleFileAdapter, ProviderAdapter
import uvicorn

app = FastAPI(title="cricx-jac")
manager = MatchStateManager()

# simple broadcaster
class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, match_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(match_id, []).append(websocket)

    def disconnect(self, match_id: str, websocket: WebSocket):
        self.active.get(match_id, []).remove(websocket)

    async def broadcast(self, match_id: str, message: dict):
        conns = self.active.get(match_id, [])
        for ws in conns:
            await ws.send_json(message)

conn_mgr = ConnectionManager()

@app.post('/events')
async def ingest_event(event: Event):
    snap = manager.apply_event(event)
    raw = manager.get_raw_state(event.match_id)
    metrics = compute_metrics(raw)
    payload = {'state': snap.dict(), 'metrics': metrics}
    # broadcast
    await conn_mgr.broadcast(event.match_id, payload)
    return {'ok': True, 'state': snap.dict(), 'metrics': metrics}

@app.get('/matches/{match_id}/state')
async def get_state(match_id: str):
    snap = manager.snapshot(match_id)
    if not snap:
        return {'error': 'not found'}
    return snap.dict()

@app.get('/matches/{match_id}/metrics')
async def get_metrics(match_id: str):
    raw = manager.get_raw_state(match_id)
    if not raw:
        return {'error': 'not found'}
    return compute_metrics(raw)

@app.websocket('/matches/{match_id}/stream')
async def ws_endpoint(websocket: WebSocket, match_id: str):
    await conn_mgr.connect(match_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        conn_mgr.disconnect(match_id, websocket)

# background feed starter
@app.on_event('startup')
async def startup_event():
    provider = os.getenv('LIVE_FEED_PROVIDER', 'sample')
    if provider == 'sample':
        path = os.getenv('SAMPLE_FEED_PATH', 'samples/sample_feed.jsonl')
        adapter = SampleFileAdapter(callback=lambda e: asyncio.create_task(_post_event(e)), path=path, delay=float(os.getenv('LIVE_FEED_POLL_INTERVAL', '1.0')))
    else:
        cfg = {'url': os.getenv('LIVE_FEED_URL')}
        adapter = ProviderAdapter(callback=lambda e: asyncio.create_task(_post_event(e)), provider_cfg=cfg)
    asyncio.create_task(adapter.start())

async def _post_event(event_dict: dict):
    # convert and call ingest_event
    try:
        ev = Event(**event_dict)
    except Exception as e:
        print('invalid event', e)
        return
    await ingest_event(ev)

if __name__ == '__main__':
    uvicorn.run('app.main:app', host=os.getenv('FASTAPI_HOST', '0.0.0.0'), port=int(os.getenv('FASTAPI_PORT', '8000')))
