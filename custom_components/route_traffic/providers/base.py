"""Incident providers report road incidents that may affect a route."""

from __future__ import annotations

import abc

from aiohttp import ClientSession

from ..models import Incident


class IncidentError(Exception):
    """Raised when a provider cannot deliver incidents."""


class IncidentProvider(abc.ABC):
    """Base class for traffic incident providers."""

    name: str = ""

    @abc.abstractmethod
    async def async_fetch_incidents(
        self, session: ClientSession
    ) -> list[Incident]:
        """Return every active incident known to the provider."""
