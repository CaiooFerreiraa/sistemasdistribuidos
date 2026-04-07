from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException


UPSTREAM_BASE_URL = os.getenv("UPSTREAM_BASE_URL", "http://127.0.0.1:8000")
POLL_INTERVAL_SECONDS = int(os.getenv("REPLICA_POLL_INTERVAL_SECONDS", "60"))
RELEASE_DELAY_SECONDS = int(os.getenv("RELEASE_DELAY_SECONDS", "60"))
RETRY_AFTER_ERROR_SECONDS = int(os.getenv("RETRY_AFTER_ERROR_SECONDS", "5"))
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(exist_ok=True)
SNAPSHOT_FILE = LOGS_DIR / "published_snapshot.json"


def _write_snapshot(snapshot: dict[str, Any]) -> None:
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_snapshot() -> dict[str, Any] | None:
    if not SNAPSHOT_FILE.exists():
        return None
    try:
        return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


logger = logging.getLogger("temperature-delayed-replica")
if not logger.handlers:
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOGS_DIR / "delayed.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False


class DelayedReplicaState:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=20.0)
        self._task: asyncio.Task[None] | None = None
        self.queue: list[dict[str, Any]] = []
        self.published_snapshot: dict[str, Any] | None = None
        self.last_pull_at: str | None = None
        self.last_error: str | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._poll_forever(), name="delayed-replica-poll")
        logger.info(
            "Replica iniciada: upstream=%s polling=%s segundos atraso=%s segundos",
            UPSTREAM_BASE_URL,
            POLL_INTERVAL_SECONDS,
            RELEASE_DELAY_SECONDS,
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._client.aclose()

    async def _poll_forever(self) -> None:
        while True:
            try:
                await self.pull_once()
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
            except Exception as exc:
                self.last_error = str(exc)
                logger.exception(
                    "Falha ao consultar o servidor de origem. Nova tentativa em %s segundos.",
                    RETRY_AFTER_ERROR_SECONDS,
                )
                await asyncio.sleep(RETRY_AFTER_ERROR_SECONDS)

    async def pull_once(self) -> None:
        response = await self._client.get(f"{UPSTREAM_BASE_URL}/temperature/latest")
        response.raise_for_status()
        upstream_snapshot = response.json()

        now = datetime.now(UTC)
        self.last_pull_at = now.isoformat()
        logger.info(
            "Snapshot recebido da origem: temperatura=%s°C observado_em=%s puxado_em=%s",
            upstream_snapshot.get("temperature_celsius"),
            upstream_snapshot.get("source_observed_at"),
            self.last_pull_at,
        )
        self.queue.append(
            {
                "release_at": (now + timedelta(seconds=RELEASE_DELAY_SECONDS)).isoformat(),
                "pulled_at": now.isoformat(),
                "upstream_snapshot": upstream_snapshot,
            }
        )
        self._promote_ready_snapshots()
        self.last_error = None

    def _promote_ready_snapshots(self) -> None:
        now = datetime.now(UTC)
        ready_items = [item for item in self.queue if datetime.fromisoformat(item["release_at"]) <= now]
        self.queue = [item for item in self.queue if datetime.fromisoformat(item["release_at"]) > now]

        for item in ready_items:
            snapshot = dict(item["upstream_snapshot"])
            snapshot["replica_pulled_at"] = item["pulled_at"]
            snapshot["replica_published_at"] = now.isoformat()
            snapshot["replica_delay_seconds"] = RELEASE_DELAY_SECONDS
            self.published_snapshot = snapshot
            _write_snapshot(snapshot)
            logger.info(
                "Snapshot publicado pela replica: temperatura=%s°C observado_em=%s puxado_em=%s publicado_em=%s",
                snapshot.get("temperature_celsius"),
                snapshot.get("source_observed_at"),
                snapshot.get("replica_pulled_at"),
                snapshot.get("replica_published_at"),
            )

    def queue_status(self) -> dict[str, Any]:
        self._promote_ready_snapshots()
        return {
            "queued_items": len(self.queue),
            "last_pull_at": self.last_pull_at,
            "last_error": self.last_error,
            "has_published_snapshot": _read_snapshot() is not None,
        }


state = DelayedReplicaState()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await state.start()
    try:
        yield
    finally:
        await state.stop()


app = FastAPI(
    title="Servidor Replica Atrasado",
    version="1.0.0",
    description="Consulta o servidor de origem a cada 1 minuto e publica o dado com atraso intencional de 1 minuto.",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "temperature-delayed-replica",
        "upstream_base_url": UPSTREAM_BASE_URL,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "release_delay_seconds": RELEASE_DELAY_SECONDS,
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    status = "degraded" if state.last_error else "ok" if state.published_snapshot else "starting"
    return {
        "status": status,
        **state.queue_status(),
    }


@app.get("/temperature/latest")
async def temperature_latest() -> dict[str, Any]:
    state._promote_ready_snapshots()
    snapshot = _read_snapshot()
    if not snapshot:
        raise HTTPException(
            status_code=503,
            detail="A replica ainda nao publicou um dado. Aguarde pelo menos 1 minuto apos a inicializacao.",
        )
    return snapshot


@app.get("/payload")
async def payload() -> dict[str, Any]:
    state._promote_ready_snapshots()
    snapshot = _read_snapshot()
    if not snapshot:
        raise HTTPException(
            status_code=503,
            detail="A replica ainda nao publicou um dado. Aguarde pelo menos 1 minuto apos a inicializacao.",
        )

    return {
        "city": snapshot.get("city"),
        "country": snapshot.get("country"),
        "temperature_celsius": snapshot.get("temperature_celsius"),
        "observed_at": snapshot.get("source_observed_at"),
        "fetched_at": snapshot.get("fetched_at"),
        "replica_pulled_at": snapshot.get("replica_pulled_at"),
        "replica_published_at": snapshot.get("replica_published_at"),
        "replica_delay_seconds": snapshot.get("replica_delay_seconds"),
    }


@app.get("/temperature/pipeline")
async def temperature_pipeline() -> dict[str, Any]:
    return {
        "published_snapshot": _read_snapshot(),
        "queue": state.queue,
        "status": state.queue_status(),
    }
