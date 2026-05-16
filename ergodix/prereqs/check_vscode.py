"""
Cantilever prereq A7 (per ADR 0003): install/verify VS Code + extensions.

A7 lands the editor side of the writer floater's tool-chain. Two stages:

  1. Visual Studio Code itself, via ``brew install --cask visual-studio-code``.
     Adds the ``code`` CLI to PATH so subsequent extension installs work.
  2. The small set of extensions ergodic-text editing depends on:
        - ``shd101wyy.markdown-preview-enhanced``
            Live Pandoc-aware Markdown preview alongside the source pane.
        - ``valentjn.vscode-ltex``
            LTeX grammar/style checker — runs locally, no cloud round-trip.
        - ``bumkaka.criticmarkup``
            Highlights ``CriticMarkup`` change marks ({++ ++}, {-- --}, etc.)
            so editor-style review notes are visually distinct from prose.
        - ``cweijan.vscode-office``
            WYSIWYG Markdown editor (Vditor-based). Right-click a ``.md``
            file → "Open With" → "Markdown Editor" for rich-text-style
            editing. Important for authors migrating from Google Docs /
            Word who want a familiar editing surface inside VS Code rather
            than only the source-view default.

A7 depends on A2 (Homebrew) for the cask install. The registry orders
A2 before A7 so this works in a single cantilever run.

Idempotent: a re-run with VS Code + all extensions already present is
a no-op — inspect returns ``ok``; apply (if reached) re-checks and
calls neither brew nor ``code``.

Per Spike 0008 / Story 0.11: brew calls set ``HOMEBREW_NO_AUTO_UPDATE=1``
so Homebrew doesn't surprise the user with a multi-minute self-update.

Network: required (downloads VS Code + extensions).
Admin: required when VS Code itself is missing — the cask writes to
``/Applications``. Extensions don't need admin (they install per-user).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ergodix.prereqs.types import ApplyResult, InspectResult

OP_ID = "A7"
DESCRIPTION = "Install/verify VS Code + ergodic-text editing extensions"

REQUIRED_EXTENSIONS: tuple[str, ...] = (
    "shd101wyy.markdown-preview-enhanced",
    "valentjn.vscode-ltex",
    "bumkaka.criticmarkup",
    "cweijan.vscode-office",
)

# Fallback path for the `code` CLI on macOS when PATH hasn't picked up
# the symlink that brew --cask installed (e.g. cantilever still running
# in the same shell session as the install).
_MAC_APP_BUNDLE_CODE = Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")


def _resolve_code_command() -> list[str] | None:
    """Return the argv prefix used to invoke the `code` CLI, or None if
    VS Code isn't installed at all. PATH check first, app-bundle fallback
    second."""
    if shutil.which("code") is not None:
        return ["code"]
    if _MAC_APP_BUNDLE_CODE.exists():
        return [str(_MAC_APP_BUNDLE_CODE)]
    return None


def _list_installed_extensions(code_cmd: list[str]) -> set[str]:
    """Return the set of extension IDs reported by `code --list-extensions`.
    Empty set on any failure (caller decides whether that's recoverable)."""
    try:
        result = subprocess.run(
            [*code_cmd, "--list-extensions"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def inspect() -> InspectResult:
    code_cmd = _resolve_code_command()
    if code_cmd is None:
        return InspectResult(
            op_id=OP_ID,
            status="needs-install",
            description=DESCRIPTION,
            current_state="VS Code (`code` CLI) not found on PATH",
            proposed_action=(
                f"brew install --cask visual-studio-code, then install "
                f"{len(REQUIRED_EXTENSIONS)} extensions"
            ),
            needs_admin=True,
            estimated_seconds=90,
            network_required=True,
        )

    installed = _list_installed_extensions(code_cmd)
    missing = [e for e in REQUIRED_EXTENSIONS if e not in installed]
    if missing:
        return InspectResult(
            op_id=OP_ID,
            status="needs-install",
            description=DESCRIPTION,
            current_state=(f"VS Code at {code_cmd[0]}; missing extensions: {', '.join(missing)}"),
            proposed_action=(f"code --install-extension <id> for {len(missing)} extension(s)"),
            needs_admin=False,
            estimated_seconds=10 * len(missing),
            network_required=True,
        )

    return InspectResult(
        op_id=OP_ID,
        status="ok",
        description=DESCRIPTION,
        current_state=(
            f"VS Code at {code_cmd[0]} with all {len(REQUIRED_EXTENSIONS)} required extensions"
        ),
        proposed_action=None,
        network_required=True,
    )


def _install_vscode_cask() -> ApplyResult | None:
    """Run `brew install --cask visual-studio-code`. Return None on success,
    or a failed ApplyResult to short-circuit."""
    env = dict(os.environ)
    env["HOMEBREW_NO_AUTO_UPDATE"] = "1"

    try:
        result = subprocess.run(
            ["brew", "install", "--cask", "visual-studio-code"],  # noqa: S607
            check=False,
            env=env,
        )
    except FileNotFoundError:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message="brew not found at apply time (A2 must run first)",
            remediation_hint=(
                "Re-run cantilever after A2 (Install/verify Homebrew) succeeds, "
                "or install VS Code manually from https://code.visualstudio.com/."
            ),
        )
    except OSError as exc:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"could not spawn brew install: {exc}",
            remediation_hint="Try `brew install --cask visual-studio-code` manually.",
        )

    if result.returncode != 0:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"brew install --cask visual-studio-code exited {result.returncode}",
            remediation_hint=(
                "Run `brew install --cask visual-studio-code` manually, or download "
                "VS Code from https://code.visualstudio.com/."
            ),
        )
    return None


def apply() -> ApplyResult:
    code_cmd = _resolve_code_command()

    if code_cmd is None:
        cask_failure = _install_vscode_cask()
        if cask_failure is not None:
            return cask_failure
        # Re-resolve after the install — PATH may now have `code`, or the
        # app-bundle fallback resolves it.
        code_cmd = _resolve_code_command()
        if code_cmd is None:
            return ApplyResult(
                op_id=OP_ID,
                status="failed",
                message=(
                    "VS Code installed but `code` CLI still not resolvable; "
                    "extensions cannot be installed in this run"
                ),
                remediation_hint=(
                    "Restart your shell so PATH picks up the `code` symlink, "
                    "then re-run cantilever to install the extensions."
                ),
            )

    installed = _list_installed_extensions(code_cmd)
    missing = [e for e in REQUIRED_EXTENSIONS if e not in installed]
    failed_extensions: list[str] = []
    for ext in missing:
        try:
            result = subprocess.run(
                [*code_cmd, "--install-extension", ext],
                check=False,
            )
        except (FileNotFoundError, OSError):
            failed_extensions.append(ext)
            continue
        if result.returncode != 0:
            failed_extensions.append(ext)

    if failed_extensions:
        return ApplyResult(
            op_id=OP_ID,
            status="failed",
            message=f"failed to install extension(s): {', '.join(failed_extensions)}",
            remediation_hint=(
                "Open VS Code and install the extension(s) from the Marketplace, "
                f"or run `code --install-extension {failed_extensions[0]}` from a "
                "fresh shell."
            ),
        )

    if missing:
        return ApplyResult(
            op_id=OP_ID,
            status="ok",
            message=f"VS Code ready; installed {len(missing)} extension(s)",
        )
    return ApplyResult(
        op_id=OP_ID,
        status="ok",
        message="VS Code installed; required extensions already present",
    )
