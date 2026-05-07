import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.routes import alerts, prices, pulse, scan, watchlist
from api.websocket import manager
from scheduler.jobs import setup as setup_scheduler
from services.mongo_service import close as close_mongo, setup_indexes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_indexes()
    setup_scheduler()

    from bot import build, start as start_bot, stop as stop_bot
    bot_app = build()
    if bot_app:
        await start_bot(bot_app)

    yield

    if bot_app:
        await stop_bot(bot_app)
    close_mongo()


app = FastAPI(title="TickTracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(watchlist.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(prices.router, prefix="/api")
app.include_router(scan.router, prefix="/api")
app.include_router(pulse.router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/health")
async def health():
    return {"status": "ok"}
