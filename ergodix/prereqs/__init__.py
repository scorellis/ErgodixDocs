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

from collections.abc import Callable
from types import ModuleType

from ergodix.prereqs import (
    check_credential_store,
    check_gh_auth,
    check_git_config,
    check_homebrew,
    check_local_config,
    check_platform,
)
from ergodix.prereqs.types import ApplyResult, InspectResult

# Registration order = cantilever execution order. A1 (platform) runs
# first because it halts cantilever on unsupported systems. A2 (Homebrew)
# follows because every other Tier-2 prereq (A3 Pandoc, A4 MacTeX, A7
# VS Code, B1 Drive Desktop) installs via brew. The C-tier prereqs (repo
# + auth scaffolding) are independent of brew; C1 (gh auth) precedes its
# dependents (C2 clone, D6 signing key) per ADR 0012's dependency analysis.
_REGISTERED_MODULES: list[ModuleType] = [
    check_platform,
    check_homebrew,
    check_local_config,
    check_credential_store,
    check_gh_auth,
    check_git_config,
]


class ModulePrereq:
    """Adapt a prereq module (OP_ID + inspect + apply [+ interactive_complete])
    to the PrereqSpec protocol used by ``ergodix.cantilever``.

    Interactive (configure-phase) support is opt-in per module: a module
    that ever returns ``status="needs-interactive"`` from ``inspect()``
    must also define an ``interactive_complete(prompt_fn)`` function. The
    adapter detects its absence and surfaces a clear failure rather than
    raising ``AttributeError`` mid-orchestration. Modules that never
    report needs-interactive don't need to define the function at all.
    """

    def __init__(self, module: ModuleType) -> None:
        self.op_id: str = module.OP_ID
        self._module = module

    def inspect(self) -> InspectResult:
        result: InspectResult = self._module.inspect()
        return result

    def apply(self) -> ApplyResult:
        result: ApplyResult = self._module.apply()
        return result

    def interactive_complete(self, prompt_fn: Callable[[str, bool], str | None]) -> ApplyResult:
        fn = getattr(self._module, "interactive_complete", None)
        if fn is None:
            return ApplyResult(
                op_id=self.op_id,
                status="failed",
                message=(
                    f"prereq {self.op_id} reported needs-interactive but the module "
                    "does not define interactive_complete(prompt_fn)"
                ),
                remediation_hint=(
                    "Prereq-module bug: add an interactive_complete(prompt_fn) function "
                    "or change inspect() to return a non-interactive status."
                ),
            )
        result: ApplyResult = fn(prompt_fn)
        return result


def all_prereqs() -> list[ModulePrereq]:
    """Return the ordered list of registered prereq adapters."""
    return [ModulePrereq(m) for m in _REGISTERED_MODULES]
