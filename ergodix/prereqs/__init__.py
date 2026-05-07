"""
Prereq registry.

Each prereq lives as a module under this package. To register a new
prereq, import it below and add it to ``_REGISTERED_MODULES``.
``all_prereqs()`` returns the ordered list of adapter objects ready
to hand to ``ergodix.cantilever.run_cantilever``.

This is the v1 explicit registry — straightforward, debuggable, and
fine for the 25 ops in ADR 0003. If we ever scale past that count,
we can switch to importlib-based directory discovery without
changing the public API.
"""

from __future__ import annotations

from types import ModuleType

from ergodix.prereqs import check_platform
from ergodix.prereqs.types import ApplyResult, InspectResult

_REGISTERED_MODULES: list[ModuleType] = [
    check_platform,
]


class ModulePrereq:
    """Adapt a prereq module (OP_ID + inspect + apply) to the PrereqSpec protocol."""

    def __init__(self, module: ModuleType) -> None:
        self.op_id: str = module.OP_ID
        self._module = module

    def inspect(self) -> InspectResult:
        result: InspectResult = self._module.inspect()
        return result

    def apply(self) -> ApplyResult:
        result: ApplyResult = self._module.apply()
        return result


def all_prereqs() -> list[ModulePrereq]:
    """Return the ordered list of registered prereq adapters."""
    return [ModulePrereq(m) for m in _REGISTERED_MODULES]
