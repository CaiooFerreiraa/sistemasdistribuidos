from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(slots=True)
class CityCoordinates:
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str


class WeatherClient:
    def __init__(self, timeout: float = 20.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def resolve_city(self, city: str, country_code: str | None = None) -> CityCoordinates:
        params = {
            "name": city,
            "count": 1,
            "language": "pt",
            "format": "json",
        }
        if country_code:
            params["countryCode"] = country_code

        response = await self._client.get(GEOCODING_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        if not results:
            raise ValueError(f"Nenhuma cidade encontrada para '{city}'.")

        item = results[0]
        return CityCoordinates(
            name=item["name"],
            country=item.get("country", "Desconhecido"),
            latitude=item["latitude"],
            longitude=item["longitude"],
            timezone=item.get("timezone", "UTC"),
        )

    async def fetch_temperature(self, coordinates: CityCoordinates) -> dict[str, Any]:
        response = await self._client.get(
            FORECAST_URL,
            params={
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude,
                "current": "temperature_2m",
                "timezone": "auto",
            },
        )
        response.raise_for_status()
        payload = response.json()
        current = payload["current"]

        return {
            "city": coordinates.name,
            "country": coordinates.country,
            "latitude": coordinates.latitude,
            "longitude": coordinates.longitude,
            "timezone": payload.get("timezone", coordinates.timezone),
            "temperature_celsius": current["temperature_2m"],
            "source_observed_at": current["time"],
            "source_interval_seconds": current.get("interval"),
        }
