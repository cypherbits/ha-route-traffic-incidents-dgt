"""Incident providers."""

from __future__ import annotations

from .base import IncidentError, IncidentProvider
from .dgt import DgtIncidentProvider, parse_feed

PROVIDERS: dict[str, type[IncidentProvider]] = {
    "dgt": DgtIncidentProvider,
}

__all__ = ["IncidentError", "IncidentProvider", "PROVIDERS", "parse_feed"]
