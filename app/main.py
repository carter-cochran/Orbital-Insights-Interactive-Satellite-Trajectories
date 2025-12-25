from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from skyfield.api import EarthSatellite, load

from app.tle_cache import TLECache

REFRESH_INTERVAL = timedelta(hours=6)

app = FastAPI(title="Orbital Insights API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

tle_cache = TLECache(refresh_interval=REFRESH_INTERVAL)

ts = load.timescale()


def isoformat_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def build_czml_packet(
    sat_id: str,
    name: str,
    interval: str,
    epoch: datetime,
    samples: List[float],
    duration_seconds: int,
) -> dict:
    return {
        "id": f"sat-{sat_id}",
        "name": name,
        "availability": interval,
        "position": {
            "epoch": isoformat_z(epoch),
            "cartographicDegrees": samples,
        },
        "point": {
            "pixelSize": 6,
            "color": {"rgba": [0, 255, 255, 255]},
        },
        "label": {
            "text": name,
            "font": "11px sans-serif",
            "style": "FILL_AND_OUTLINE",
            "outlineWidth": 2,
            "horizontalOrigin": "LEFT",
            "pixelOffset": {"cartesian2": [8, 0]},
        },
        "path": {
            "show": True,
            "leadTime": 0,
            "trailTime": duration_seconds,
            "width": 1,
            "material": {
                "solidColor": {"color": {"rgba": [0, 255, 255, 180]}}
            },
        },
    }


def build_samples(
    satellite: EarthSatellite,
    start: datetime,
    minutes: int,
    step_seconds: int,
) -> List[float]:
    duration_seconds = minutes * 60
    offsets = np.arange(0, duration_seconds + 1, step_seconds, dtype=float)
    datetimes = [start + timedelta(seconds=float(offset)) for offset in offsets]
    times = ts.from_datetimes(datetimes)
    subpoints = satellite.at(times).subpoint()
    lats = subpoints.latitude.degrees
    lons = subpoints.longitude.degrees
    heights = subpoints.elevation.m
    samples: List[float] = []
    for offset, lon, lat, height in zip(offsets, lons, lats, heights):
        normalized_lon = ((lon + 180.0) % 360.0) - 180.0
        samples.extend([float(offset), float(normalized_lon), float(lat), float(height)])
    return samples


@app.get("/api/health")
async def health() -> dict:
    tle_cache.refresh_if_needed()
    last_refresh = tle_cache.last_refresh_utc
    return {
        "status": "ok",
        "last_refresh_utc": isoformat_z(last_refresh) if last_refresh else None,
        "count": tle_cache.count,
    }


@app.get("/api/satellites")
async def satellites(limit: int = Query(200, ge=1, le=2000)) -> list:
    tle_cache.refresh_if_needed()
    return tle_cache.list_satellites(limit)


@app.get("/api/czml")
async def czml(
    ids: str = Query(..., description="Comma-separated NORAD IDs"),
    minutes: int = Query(90, ge=1, le=360),
    step: int = Query(10, ge=5, le=60),
) -> dict:
    tle_cache.refresh_if_needed()

    requested_ids = [item.strip() for item in ids.split(",") if item.strip()]
    used: List[str] = []
    skipped: List[str] = []

    start = datetime.now(timezone.utc)
    minutes = clamp_int(minutes, 1, 360)
    step = clamp_int(step, 5, 60)
    duration_seconds = minutes * 60
    end = start + timedelta(minutes=minutes)
    interval = f"{isoformat_z(start)}/{isoformat_z(end)}"

    czml_packets: List[dict] = [
        {
            "id": "document",
            "version": "1.0",
            "clock": {
                "interval": interval,
                "currentTime": isoformat_z(start),
                "multiplier": 60,
                "range": "LOOP_STOP",
                "step": "SYSTEM_CLOCK_MULTIPLIER",
            },
        }
    ]

    for norad_id in requested_ids:
        record = tle_cache.get(norad_id)
        if not record:
            skipped.append(norad_id)
            continue
        satellite = EarthSatellite(record.line1, record.line2, record.name, ts)
        samples = build_samples(satellite, start, minutes, step)
        czml_packets.append(
            build_czml_packet(
                sat_id=record.norad_id,
                name=record.name,
                interval=interval,
                epoch=start,
                samples=samples,
                duration_seconds=duration_seconds,
            )
        )
        used.append(record.norad_id)

    return {"czml": czml_packets, "used": used, "skipped": skipped}
