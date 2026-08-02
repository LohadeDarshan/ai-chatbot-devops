import time
import logging

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from . import models, schemas
from .database import engine, get_db, Base
from .ollama_client import generate_reply, OLLAMA_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot-api")


def init_db_with_retry(max_attempts: int = 10, delay_seconds: int = 5) -> None:
    """
    Create DB tables on startup (simple approach; use Alembic for production).

    Postgres may not be reachable in the first few seconds after this pod
    starts (e.g. the postgres pod is still initializing, or DNS/service
    routing hasn't settled). Instead of crashing immediately and forcing
    Kubernetes to restart the whole container, retry with a short delay
    so the container stays up long enough for readiness/startup probes
    to keep polling /health.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables ready (attempt %d/%d).", attempt, max_attempts)
            return
        except Exception as exc:
            logger.warning(
                "DB not ready yet (attempt %d/%d): %s", attempt, max_attempts, exc
            )
            if attempt == max_attempts:
                logger.error("Giving up on DB initialization after %d attempts.", max_attempts)
                raise
            time.sleep(delay_seconds)


init_db_with_retry()

app = FastAPI(
    title="AI Chatbot API",
    description="FastAPI backend for the AI Chatbot DevOps demo project",
    version="1.0.0",
)

# Allow the frontend (served from a different origin/port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Prometheus metrics ----
REQUEST_COUNT = Counter(
    "chatbot_requests_total", "Total number of chat requests", ["endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "chatbot_request_latency_seconds", "Latency of chat requests", ["endpoint"]
)


@app.get("/", tags=["meta"])
def root():
    return {
        "message": "AI Chatbot API is running 🚀",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health", response_model=schemas.HealthResponse, tags=["meta"])
def health(db: Session = Depends(get_db)):
    """Used by Kubernetes liveness/readiness probes."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        db_status = "down"

    return schemas.HealthResponse(
        status="ok",
        database=db_status,
        model_backend=OLLAMA_MODEL,
    )


@app.get("/metrics", tags=["meta"])
def metrics():
    """Prometheus scrapes this endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/chat", response_model=schemas.ChatResponse, tags=["chat"])
async def chat(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    """
    Receive a user message, get a reply from the open-source LLM (via Ollama),
    persist the conversation turn in Postgres, and return the bot's reply.
    """
    start = time.time()
    endpoint = "/api/chat"

    if not req.message.strip():
        REQUEST_COUNT.labels(endpoint=endpoint, status="400").inc()
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        bot_reply = await generate_reply(req.message)

        chat_row = models.ChatMessage(
            session_id=req.session_id,
            user_message=req.message,
            bot_response=bot_reply,
        )
        db.add(chat_row)
        db.commit()
        db.refresh(chat_row)

        REQUEST_COUNT.labels(endpoint=endpoint, status="200").inc()
        return chat_row

    except Exception as e:
        db.rollback()
        REQUEST_COUNT.labels(endpoint=endpoint, status="500").inc()
        logger.exception("Error handling chat request")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start)


@app.get("/api/history/{session_id}", response_model=list[schemas.HistoryItem], tags=["chat"])
def history(session_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Return recent chat history for a given session, oldest first."""
    rows = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))