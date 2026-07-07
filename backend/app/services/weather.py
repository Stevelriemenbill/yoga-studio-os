"""Weather integration adapter.

Provides a pluggable interface for a weather API (e.g. OpenWeather). The
default implementation returns a neutral forecast so the system works without
external credentials; a real provider can be injected later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WeatherForecast:
    temperature_c: float | None
    condition: str  # e.g. "clear", "rain", "snow", "heat"
    description: str


class WeatherProvider:
    async def forecast_for(
        self, lat: float | None, lon: float | None, when: datetime
    ) -> WeatherForecast:
        raise NotImplementedError


class NullWeatherProvider(WeatherProvider):
    """No external calls; returns a neutral forecast."""

    async def forecast_for(
        self, lat: float | None, lon: float | None, when: datetime
    ) -> WeatherForecast:
        return WeatherForecast(
            temperature_c=None, condition="unknown", description=""
        )


_provider: WeatherProvider = NullWeatherProvider()


def get_weather_provider() -> WeatherProvider:
    return _provider


def set_weather_provider(provider: WeatherProvider) -> None:
    global _provider
    _provider = provider


def weather_advice(forecast: WeatherForecast) -> str:
    """Human-friendly advice used inside smart reminders."""
    if forecast.condition == "heat" or (
        forecast.temperature_c is not None and forecast.temperature_c >= 28
    ):
        return "Morgen wird es warm. Bitte ausreichend trinken und 10 Minuten früher erscheinen."
    if forecast.condition == "rain":
        return "Es könnte regnen – plane etwas mehr Zeit für die Anreise ein."
    if forecast.condition == "snow":
        return "Schnee möglich – fahre vorsichtig und komme lieber etwas früher."
    return ""
