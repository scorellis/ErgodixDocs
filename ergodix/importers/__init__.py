"""
Importer plugin registry.

Each importer module under this package declares the file types it
recognizes and how to extract their contents into Pandoc-Markdown
suitable for the rest of the corpus pipeline. The migrate command
(`ergodix migrate --from <name>`, per ADR 0015) dispatches to a plugin
by NAME.

A registered importer module exposes:

    NAME: str
        Short identifier matching ``--from <NAME>``. Lowercase.

    EXTENSIONS: tuple[str, ...]
        File extensions claimed by this importer, lowercase, with the
        leading dot (e.g. ``(".gdoc",)``).

    extract(path: pathlib.Path, **kwargs: Any) -> str
        Read the source file and return Pandoc-Markdown content. Importer
        plugins may accept extra keyword-only arguments (the gdocs
        importer takes ``docs_service``, for example) but must accept
        ``path`` positionally.

To add an importer, drop a module in this package and append it to
``_REGISTERED_MODULES`` below. Like ``ergodix.prereqs``, this is a v1
explicit registry — straightforward and debuggable. Switch to
importlib-based discovery only when the cost of the explicit list
becomes obviously larger than the benefit of compile-time imports.
"""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType
from typing import Any

from ergodix.importers import docx, gdocs

_REGISTERED_MODULES: list[ModuleType] = [
    gdocs,
    docx,
]


class Importer:
    """Adapter wrapping an importer module for typed access.

    The adapter normalizes ``EXTENSIONS`` to lowercase and exposes
    ``extract`` as a bound method, so callers don't reach into the
    module's globals.
    """

    def __init__(self, module: ModuleType) -> None:
        self.name: str = module.NAME
        self.extensions: tuple[str, ...] = tuple(e.lower() for e in module.EXTENSIONS)
        self._extract: Callable[..., str] = module.extract

    def extract(self, *args: Any, **kwargs: Any) -> str:
        return self._extract(*args, **kwargs)


def _adapters() -> list[Importer]:
    return [Importer(m) for m in _REGISTERED_MODULES]


def available_importers() -> list[str]:
    """Return registered importer names, in registration order."""
    return [a.name for a in _adapters()]


def get_importer(name: str) -> Importer:
    """Look up an importer by NAME. Raises KeyError if not registered."""
    for adapter in _adapters():
        if adapter.name == name:
            return adapter
    raise KeyError(f"unknown importer: {name!r}")


def extension_to_importer(ext: str) -> Importer | None:
    """Return the first importer that claims ``ext``, or None.

    The lookup is case-insensitive on the extension. The leading dot is
    required — ``"gdoc"`` (no dot) returns None.
    """
    if not ext.startswith("."):
        return None
    needle = ext.lower()
    for adapter in _adapters():
        if needle in adapter.extensions:
            return adapter
    return None
