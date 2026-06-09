from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite import SqliteSaver

from agents.graph import build_graph
from app.routes import router
from core.config import settings
from core.llm import get_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    app.state.graph = build_graph(llm=get_llm(), checkpointer=saver)
    try:
        yield
    finally:
        conn.close()


app = FastAPI(title="JapanLife", version="0.2.0", lifespan=lifespan)
app.include_router(router)
