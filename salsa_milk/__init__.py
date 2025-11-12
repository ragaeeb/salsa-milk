"""Project metadata for the Salsa Milk toolkit."""

from __future__ import annotations

from importlib import metadata

__all__ = ["__version__", "get_version"]

try:
    __version__ = metadata.version("salsa-milk")
except metadata.PackageNotFoundError:  # pragma: no cover - fallback for editable installs
    __version__ = "0.2.0"


def get_version() -> str:
    """Return the current Salsa Milk version string."""

    return __version__
