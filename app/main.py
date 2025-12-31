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
# Adapter manager: supervise adapters and expose status
adapter_manager = None

@app.on_event('startup')
async def startup_event():
    # Load adapters configured by LIVE_FEED_PROVIDERS (comma-separated)
    from app.adapters.loader import load_adapters
    from app.adapters.manager import AdapterManager
    global adapter_manager
    cb = lambda e: asyncio.create_task(_post_event(e))
    adapters = load_adapters(cb)
    adapter_manager = AdapterManager(adapters)
    # run manager in background
    asyncio.create_task(adapter_manager.start())
    for adapter in adapters:
        print(f"Registered adapter: {adapter.__class__.__name__}")

@app.get('/adapters/status')
async def adapters_status():
    if not adapter_manager:
        return {'error': 'adapter manager not started'}
    return adapter_manager.get_status()

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
