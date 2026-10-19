"""DGT incident provider, backed by the Spanish DATEX II situation feed.

The feed is published by the *Punto de Acceso Nacional de Tráfico y Movilidad*
and lists every active road situation in Spain. It needs no API key, which
makes it a good default provider.

The feed is several megabytes and is only produced roughly once a minute, so
the parsed result is cached at module level and shared by every config entry.
That way a user monitoring five routes still downloads the feed once.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Final
from xml.etree import ElementTree

from aiohttp import ClientError, ClientSession

from ..const import CLOSURE_MANAGEMENT
from ..models import Incident
from .base import IncidentError, IncidentProvider

_LOGGER = logging.getLogger(__name__)

FEED_URL: Final = (
    "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml"
)
REQUEST_TIMEOUT = 90
USER_AGENT: Final = "HomeAssistant-RouteTraffic/1.0"

#: The upstream feed advertises ``Cache-Control: max-age=60``.
FEED_CACHE_TTL = 120.0

_cache: tuple[float, list[Incident]] | None = None
_cache_lock = asyncio.Lock()

_DETAIL_TAGS: Final = frozenset(
    {
        "environmentalObstructionType",
        "vehicleObstructionType",
        "roadMaintenanceType",
        "accidentType",
        "obstructionType",
        "abnormalTrafficType",
        "poorEnvironmentType",
    }
)


def _local(tag: str) -> str:
    """Return an XML tag without its namespace."""
    return tag.rsplit("}", 1)[-1]


def _find_text(element: ElementTree.Element, name: str) -> str:
    """Return the text of the first descendant with the given local name."""
    for child in element.iter():
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def _find_detail(element: ElementTree.Element) -> str:
    """Return the most specific cause detail available."""
    for child in element.iter():
        if _local(child.tag) in _DETAIL_TAGS and child.text:
            return child.text.strip()
    return ""


def _parse_datetime(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp from the feed, tolerating offsets."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        _LOGGER.debug("Could not parse DATEX II timestamp %r", value)
        return None


def parse_feed(blob: bytes) -> list[Incident]:
    """Parse a DATEX II situation publication into incidents.

    The parser is namespace agnostic on purpose: the DGT feed uses prefixes
    that are not guaranteed to stay stable, while ElementTree always exposes
    the fully qualified ``{namespace}tag`` form.
    """
    try:
        root = ElementTree.fromstring(blob)
    except ElementTree.ParseError as err:
        raise IncidentError(f"DGT feed is not valid XML: {err}") from err

    incidents: list[Incident] = []

    for situation in root.iter():
        if _local(situation.tag) != "situation":
            continue
        situation_id = situation.get("id")
        if situation_id is None:
            continue

        points: list[tuple[float, float]] = []
        pending_lat: float | None = None
        for node in situation.iter():
            tag = _local(node.tag)
            if tag == "latitude":
                try:
                    pending_lat = float(node.text)
                except (TypeError, ValueError):
                    pending_lat = None
            elif tag == "longitude" and pending_lat is not None:
                try:
                    points.append((pending_lat, float(node.text)))
                except (TypeError, ValueError):
                    pass
                pending_lat = None

        if not points:
            continue

        management = _find_text(situation, "roadOrCarriagewayOrLaneManagementType")
        incidents.append(
            Incident(
                uid=situation_id,
                provider="dgt",
                road=_find_text(situation, "roadName"),
                severity=_find_text(situation, "overallSeverity") or "unknown",
                cause=_find_text(situation, "causeType"),
                detail=_find_detail(situation),
                management=management,
                is_closure=management in CLOSURE_MANAGEMENT,
                municipality=_find_text(situation, "municipality"),
                started_at=_parse_datetime(
                    _find_text(situation, "overallStartTime")
                ),
                points=tuple(points),
            )
        )

    return incidents


async def _async_download(session: ClientSession) -> bytes:
    """Download the raw feed."""
    try:
        async with session.get(
            FEED_URL,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as resp:
            if resp.status != 200:
                raise IncidentError(f"DGT responded with HTTP {resp.status}")
            blob = await resp.read()
    except ClientError as err:
        raise IncidentError(f"Could not reach the DGT feed: {err}") from err
    except TimeoutError as err:
        raise IncidentError("The DGT feed request timed out") from err

    if not blob:
        raise IncidentError("The DGT feed returned an empty body")
    return blob


class DgtIncidentProvider(IncidentProvider):
    """Fetch road incidents from the Spanish DGT DATEX II feed."""

    name = "dgt"

    async def async_fetch_incidents(
        self, session: ClientSession
    ) -> list[Incident]:
        """Return every active situation published by the DGT.

        Concurrent calls share a single download; the parsed result is reused
        for :data:`FEED_CACHE_TTL` seconds.
        """
        global _cache

        cached = _cache
        if cached is not None and time.monotonic() - cached[0] < FEED_CACHE_TTL:
            return cached[1]

        async with _cache_lock:
            # Another entry may have refreshed the cache while we waited.
            cached = _cache
            if cached is not None and time.monotonic() - cached[0] < FEED_CACHE_TTL:
                return cached[1]

            blob = await _async_download(session)
            incidents = parse_feed(blob)
            _cache = (time.monotonic(), incidents)
            _LOGGER.debug(
                "DGT feed refreshed: %.1f MB, %d incidents",
                len(blob) / 1_000_000,
                len(incidents),
            )
            return incidents
