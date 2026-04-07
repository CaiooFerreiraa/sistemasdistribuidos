from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from app.weather_client import CityCoordinates, WeatherClient


CITY_NAME = os.getenv("CITY_NAME", "Salvador")
COUNTRY_CODE = os.getenv("COUNTRY_CODE", "BR")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(exist_ok=True)
SNAPSHOT_FILE = LOGS_DIR / "latest_snapshot.json"


def _write_snapshot(snapshot: dict[str, Any]) -> None:
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_snapshot() -> dict[str, Any] | None:
    if not SNAPSHOT_FILE.exists():
        return None
    try:
        return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


logger = logging.getLogger("temperature-source")
if not logger.handlers:
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOGS_DIR / "source.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False


class SourceState:
    def __init__(self) -> None:
        self.weather_client = WeatherClient()
        self.coordinates: CityCoordinates | None = None
        self.latest_snapshot: dict[str, Any] | None = None
        self.last_poll_at: str | None = None
        self.last_error: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.coordinates = await self.weather_client.resolve_city(CITY_NAME, COUNTRY_CODE)
        logger.info(
            "Cidade resolvida: %s/%s (lat=%s, lon=%s, timezone=%s)",
            self.coordinates.name,
            self.coordinates.country,
            self.coordinates.latitude,
            self.coordinates.longitude,
            self.coordinates.timezone,
        )
        await self.poll_once()
        self._task = asyncio.create_task(self._poll_forever(), name="source-weather-poll")
        logger.info("Loop de polling iniciado com intervalo de %s segundos.", POLL_INTERVAL_SECONDS)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.weather_client.close()

    async def _poll_forever(self) -> None:
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                await self.poll_once()
            except Exception as exc:
                self.last_error = str(exc)
                logger.exception("Falha ao consultar temperatura.")

    async def poll_once(self) -> None:
        if not self.coordinates:
            raise RuntimeError("Coordenadas da cidade ainda nao foram carregadas.")

        snapshot = await self.weather_client.fetch_temperature(self.coordinates)
        fetched_at = datetime.now(UTC).isoformat()
        snapshot["fetched_at"] = fetched_at
        self.latest_snapshot = snapshot
        self.last_poll_at = fetched_at
        self.last_error = None
        _write_snapshot(snapshot)
        logger.info(
            "Temperatura atualizada: cidade=%s temperatura=%s°C observado_em=%s coletado_em=%s",
            snapshot["city"],
            snapshot["temperature_celsius"],
            snapshot["source_observed_at"],
            fetched_at,
        )


state = SourceState()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await state.start()
    try:
        yield
    finally:
        await state.stop()


app = FastAPI(
    title="Servidor de Origem da Temperatura",
    version="1.0.0",
    description="Consulta a temperatura atual de uma cidade em uma API publica e disponibiliza o dado por HTTP.",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "temperature-source",
        "city": CITY_NAME,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok" if _read_snapshot() else "starting",
        "city": CITY_NAME,
        "last_poll_at": state.last_poll_at,
        "last_error": state.last_error,
    }


@app.get("/temperature/latest")
async def temperature_latest() -> dict[str, Any]:
    snapshot = _read_snapshot()
    if not snapshot:
        raise HTTPException(status_code=503, detail="Aguardando a primeira leitura da temperatura.")
    return snapshot
