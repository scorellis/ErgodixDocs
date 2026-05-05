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

import click

from ergodix.version import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="ergodix")
@click.option("--writer", "writer", is_flag=True, help="Writer role floater (placeholder; see ADR 0005).")
@click.option("--editor", "editor", is_flag=True, help="Editor role floater (placeholder).")
@click.option("--developer", "developer", is_flag=True, help="Developer floater (placeholder).")
@click.option("--publisher", "publisher", is_flag=True, help="Publisher floater (placeholder).")
@click.option("--focus-reader", "focus_reader", is_flag=True, help="Focus-reader floater (mutex with the others).")
@click.option("--dry-run", "dry_run", is_flag=True, help="Behavior modifier (placeholder).")
@click.option("--verbose", "verbose", is_flag=True, help="Behavior modifier (placeholder).")
@click.option("--ci", "ci", is_flag=True, help="Behavior modifier — non-interactive (placeholder).")
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
def cantilever_cmd() -> None:
    """Bootstrap orchestrator (ADR 0003). Not yet implemented."""
    _not_yet_implemented("cantilever")


@main.command(name="migrate")
@click.option("--from", "from_", type=str, required=True, help="Importer name (e.g. gdocs, scrivener).")
def migrate_cmd(from_: str) -> None:
    """Import an existing corpus (ADR 0001). Not yet implemented."""
    _not_yet_implemented(f"migrate --from {from_}")


@main.command(name="render")
@click.argument("target", type=click.Path())
def render_cmd(target: str) -> None:
    """Render a chapter or book to PDF via Pandoc → XeLaTeX."""
    _not_yet_implemented(f"render {target}")


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
    """Read-only health check."""
    _not_yet_implemented("status")


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
