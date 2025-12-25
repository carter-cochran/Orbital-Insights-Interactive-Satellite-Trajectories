from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import httpx

CELESTRAK_TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"


@dataclass
class TLERecord:
    norad_id: str
    name: str
    line1: str
    line2: str
    fetched_at_utc: datetime


class TLECache:
    def __init__(self, refresh_interval: timedelta) -> None:
        self.refresh_interval = refresh_interval
        self._records: Dict[str, TLERecord] = {}
        self._last_refresh_utc: Optional[datetime] = None

    @property
    def last_refresh_utc(self) -> Optional[datetime]:
        return self._last_refresh_utc

    @property
    def count(self) -> int:
        return len(self._records)

    def get(self, norad_id: str) -> Optional[TLERecord]:
        return self._records.get(norad_id)

    def list_satellites(self, limit: int) -> list[dict]:
        items = list(self._records.values())
        items.sort(key=lambda rec: rec.norad_id)
        return [
            {"norad_id": rec.norad_id, "name": rec.name}
            for rec in items[:limit]
        ]

    def refresh_if_needed(self) -> None:
        now = datetime.now(timezone.utc)
        if self._last_refresh_utc is None:
            self._refresh(now)
            return
        if now - self._last_refresh_utc >= self.refresh_interval:
            self._refresh(now)

    def _refresh(self, now: datetime) -> None:
        tle_text = fetch_tle_text()
        records = parse_tle_records(tle_text, now)
        self._records = records
        self._last_refresh_utc = now


def fetch_tle_text() -> str:
    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(CELESTRAK_TLE_URL)
                response.raise_for_status()
                return response.text
        except Exception as exc:  # noqa: BLE001 - surface as 500
            last_error = exc
            if attempt == 0:
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Unable to fetch TLE data")


def parse_tle_records(tle_text: str, fetched_at_utc: datetime) -> Dict[str, TLERecord]:
    lines = [line.strip() for line in tle_text.splitlines() if line.strip()]
    records: Dict[str, TLERecord] = {}
    for idx in range(0, len(lines) - 2, 3):
        name = lines[idx]
        line1 = lines[idx + 1]
        line2 = lines[idx + 2]
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            continue
        norad_id = line1[2:7].strip()
        if not norad_id.isdigit():
            continue
        records[norad_id] = TLERecord(
            norad_id=norad_id,
            name=name,
            line1=line1,
            line2=line2,
            fetched_at_utc=fetched_at_utc,
        )
    return records
