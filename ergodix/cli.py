"""
ErgodixDocs CLI entry point.

Per ADR 0001, this is a Click subcommand-group CLI. Per ADR 0007, it's
registered as the `ergodix` console-script in pyproject.toml.

This module is intentionally a stub right now. Subcommands (cantilever,
migrate, render, sync-out, sync-in, status, opus, publish, ingest, auth)
land one at a time under TDD per Story 0.10. Each lands behind a failing
test in tests/test_cli_<subcommand>.py before any real implementation.

Until subcommands exist, `ergodix --help` lists what's planned and
`ergodix <anything>` exits with a clear "not yet implemented" message
rather than crashing on a missing module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from ergodix.version import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="ergodix")
@click.option("--writer", "writer", is_flag=True, help="Writer role floater (see ADR 0005).")
@click.option("--editor", "editor", is_flag=True, help="Editor role floater.")
@click.option("--developer", "developer", is_flag=True, help="Developer floater.")
@click.option("--publisher", "publisher", is_flag=True, help="Publisher floater.")
@click.option(
    "--focus-reader",
    "focus_reader",
    is_flag=True,
    help="Focus-reader floater (mutex with the others).",
)
@click.option("--dry-run", "dry_run", is_flag=True, help="Preview only.")
@click.option("--verbose", "verbose", is_flag=True, help="Detailed output.")
@click.option("--ci", "ci", is_flag=True, help="Non-interactive mode.")
@click.pass_context
def main(
    ctx: click.Context,
    writer: bool,
    editor: bool,
    developer: bool,
    publisher: bool,
    focus_reader: bool,
    dry_run: bool,
    verbose: bool,
    ci: bool,
) -> None:
    """ErgodixDocs — architectural co-authoring tool for Ergodic-text fiction."""
    # Enforce focus-reader mutex per ADR 0005.
    if focus_reader and (writer or editor or developer or publisher):
        click.echo(
            "error: --focus-reader cannot be combined with --writer / --editor / "
            "--developer / --publisher. Choose one.",
            err=True,
        )
        sys.exit(2)

    ctx.ensure_object(dict)
    ctx.obj["floaters"] = {
        "writer": writer,
        "editor": editor,
        "developer": developer,
        "publisher": publisher,
        "focus-reader": focus_reader,
        "dry-run": dry_run,
        "verbose": verbose,
        "ci": ci,
    }

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command(name="cantilever")
@click.pass_context
def cantilever_cmd(ctx: click.Context) -> None:
    """Bootstrap orchestrator (ADR 0003) — inspect, plan, consent, apply, verify."""
    from ergodix.cantilever import run_cantilever
    from ergodix.prereqs import all_prereqs

    floaters: dict[str, bool] = ctx.obj.get("floaters", {})
    result = run_cantilever(
        floaters=floaters,
        prereqs=list(all_prereqs()),
    )

    # Outcomes that represent a clean exit (user got what they asked for, no work
    # left undone in error). Everything else is exit 1 so cron / CI / wrappers
    # see the failure.
    success_outcomes = {
        "applied",
        "no-changes-needed",
        "dry-run",
        "consent-declined",
    }
    sys.exit(0 if result.outcome in success_outcomes else 1)


@main.command(name="migrate")
@click.option(
    "--from",
    "from_",
    type=str,
    required=True,
    help="Importer name (e.g. gdocs, scrivener).",
)
def migrate_cmd(from_: str) -> None:
    """Import an existing corpus (ADR 0001). Not yet implemented."""
    _not_yet_implemented(f"migrate --from {from_}")


@main.command(name="render")
@click.argument("target", type=click.Path(path_type=Path))
@click.option(
    "--output",
    "-o",
    "output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output PDF path. Defaults to <chapter>.pdf next to the source.",
)
@click.option(
    "--corpus-root",
    "corpus_root",
    type=click.Path(path_type=Path),
    default=None,
    help=(
        "Ceiling for the preamble-cascade walk. Defaults to the chapter's "
        "filesystem path (no boundary). Provide this when the chapter is "
        "deep inside a known corpus folder."
    ),
)
def render_cmd(target: Path, output: Path | None, corpus_root: Path | None) -> None:
    """Render a chapter to PDF via Pandoc → XeLaTeX (Story 0.2 pipeline).

    Walks up from the chapter collecting ``_preamble.tex`` files
    (most-general-first); passes them to Pandoc via repeated
    ``--include-in-header`` flags so LaTeX's later-wins semantics give
    leaf-most preambles override authority.
    """
    from ergodix import render as render_module

    try:
        result = render_module.render(target, output=output, corpus_root=corpus_root)
    except render_module.RenderError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Rendered: {result}")


@main.command(name="sync-out")
def sync_out_cmd() -> None:
    """Push pending edits to the editor's slice repo (ADR 0006)."""
    _not_yet_implemented("sync-out")


@main.command(name="sync-in")
def sync_in_cmd() -> None:
    """Polling-job invocation: fetch remote changes (ADR 0004)."""
    _not_yet_implemented("sync-in")


@main.command(name="status")
def status_cmd() -> None:
    """Read-only health check — show platform, prereqs, settings, sync, and credentials.

    Surfaces the same information cantilever's inspect phase produces, plus
    settings cascade values + credential presence (without values), so a user
    can quickly see "what does ErgodixDocs think the world looks like?" without
    consenting to any installer changes.

    Strictly read-only per CLAUDE.md principle #2 / ADR 0013.
    """
    import os
    import platform as platform_module

    from ergodix.auth import (
        ENV_OVERRIDES,
        KNOWN_KEYS,
        _from_file,
        _from_keyring,
    )
    from ergodix.connectivity import is_online
    from ergodix.prereqs import all_prereqs
    from ergodix.settings import load_bootstrap_settings
    from ergodix.sync_transport import (
        detect_current_sync_transport,
        read_corpus_folder_from_local_config,
    )

    # ── Header
    click.echo(f"ergodix {__version__}")
    click.echo(f"Python {sys.version.split()[0]} on {platform_module.system()}")

    # ── Sync transport + corpus folder
    corpus_folder = read_corpus_folder_from_local_config()
    mode = detect_current_sync_transport()
    click.echo()
    click.echo(f"Sync transport: {mode}")
    if corpus_folder is None:
        click.echo("Corpus folder:  (not configured in local_config.py)")
    else:
        existence = "exists" if corpus_folder.exists() else "MISSING"
        click.echo(f"Corpus folder:  {corpus_folder} ({existence})")

    # ── Settings cascade
    settings = load_bootstrap_settings()
    click.echo()
    click.echo("Settings:")
    click.echo(f"  mactex_install_size: {settings.mactex_install_size}")
    for w in settings.warnings:
        click.echo(f"  ⚠ {w}")

    # ── Prereqs (run inspect for each registered)
    click.echo()
    click.echo("Prereqs:")
    status_marker = {
        "ok": "✓",
        "needs-install": "○",
        "needs-update": "○",
        "needs-interactive": "?",
        "deferred-offline": "·",
        "failed": "✗",
    }
    for prereq in all_prereqs():
        try:
            r = prereq.inspect()
            marker = status_marker.get(r.status, " ")
            click.echo(f"  {marker} {r.op_id} ({r.status}): {r.current_state}")
        except Exception as exc:
            click.echo(f"  ! {prereq.op_id} (error inspecting): {exc}")

    # ── Credentials (presence only; values never printed)
    click.echo()
    click.echo("Credentials (presence only; values never printed):")
    for name in KNOWN_KEYS:
        sources: list[str] = []
        env_var = ENV_OVERRIDES.get(name)
        if env_var and os.environ.get(env_var):
            sources.append(f"env:{env_var}")
        try:
            if _from_keyring(name):
                sources.append("keyring")
        except Exception:
            sources.append("keyring:error")
        try:
            if _from_file(name):
                sources.append("file")
        except Exception:
            sources.append("file:error")
        cred_marker = "✓" if any(not s.endswith(":error") for s in sources) else "✗"
        src_label = ", ".join(sources) if sources else "(none)"
        click.echo(f"  {cred_marker} {name:30s} {src_label}")

    # ── Network
    click.echo()
    click.echo(f"Network: {'online' if is_online() else 'offline'}")


@main.command(name="publish")
@click.option("--editor", "editor", type=str, required=True)
def publish_cmd(editor: str) -> None:
    """Publish authorized files to an editor's slice repo (ADR 0006)."""
    _not_yet_implemented(f"publish --editor {editor}")


@main.command(name="ingest")
@click.option("--editor", "editor", type=str, required=True)
def ingest_cmd(editor: str) -> None:
    """Ingest signed edits from an editor's slice repo (ADR 0006)."""
    _not_yet_implemented(f"ingest --editor {editor}")


def _not_yet_implemented(name: str) -> None:
    click.echo(
        f"error: `ergodix {name}` is not yet implemented. "
        f"This command is a stub awaiting Story 0.10 / 0.2 implementation work.",
        err=True,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
