"""
Tests for ergodix.cli — pin the CLI surface that exists today.

Per CLAUDE.md TDD norm: every committed contract has a test. cli.py
landed as a stopgap to address an earlier "CLI not runnable" finding;
this test file now pins what was committed so future changes have to
go through the test gate.

The CLI is deliberately a stub today. These tests assert the *contract*:
- root group runs and shows help
- --version returns a string
- focus-reader mutex is enforced (per ADR 0005)
- floater flags are accepted without crash
- planned subcommands exit with the documented "not yet implemented" code
"""

from __future__ import annotations

import sys

import pytest
from click.testing import CliRunner

from ergodix.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ─── Root group ─────────────────────────────────────────────────────────────


def test_help_runs_and_lists_subcommands(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    # Every subcommand declared in cli.py must show up in --help.
    for name in (
        "cantilever",
        "migrate",
        "render",
        "sync-out",
        "sync-in",
        "status",
        "publish",
        "ingest",
    ):
        assert name in result.output


def test_version_flag_prints_version(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "ergodix" in result.output.lower()
    # Version should be a non-empty string after the program name.
    assert len(result.output.strip().split()) >= 2


def test_no_args_prints_help(runner: CliRunner) -> None:
    """Invoking with no subcommand and no flags should show help, not crash."""
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "Usage" in result.output or "Commands" in result.output


# ─── Floater flags ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "flag",
    [
        "--writer",
        "--editor",
        "--developer",
        "--publisher",
        "--focus-reader",
        "--dry-run",
        "--verbose",
        "--ci",
    ],
)
def test_floater_flag_is_accepted(runner: CliRunner, flag: str) -> None:
    """Each floater flag is recognized at the top level (no error parsing it)."""
    result = runner.invoke(main, [flag, "--help"])
    assert result.exit_code == 0


# ─── focus-reader mutex (per ADR 0005) ──────────────────────────────────────


@pytest.mark.parametrize(
    "other_flag",
    ["--writer", "--editor", "--developer", "--publisher"],
)
def test_focus_reader_mutex_blocks_combinations(runner: CliRunner, other_flag: str) -> None:
    """
    --focus-reader cannot be combined with any of the other role floaters.
    The mutex is enforced at startup with exit code 2 and a clear message.
    """
    result = runner.invoke(main, ["--focus-reader", other_flag, "cantilever"])
    assert result.exit_code == 2
    assert "focus-reader" in result.output.lower()
    assert "cannot be combined" in result.output.lower()


def test_focus_reader_alone_is_valid(runner: CliRunner) -> None:
    """--focus-reader alone (no other role floater) is allowed; mutex doesn't trip."""
    result = runner.invoke(main, ["--focus-reader", "--dry-run", "cantilever"])
    # The mutex would surface as exit 2 with "cannot be combined". Anything
    # else means the floater was accepted. Use --dry-run so this test doesn't
    # depend on the host environment passing real verify checks.
    assert result.exit_code == 0
    assert "cannot be combined" not in result.output.lower()


# ─── Subcommand stubs exit cleanly with documented "not yet implemented" ────


@pytest.mark.parametrize(
    ("cmd", "extra_args"),
    [
        # cantilever is now wired (Story 0.11 step 4) — see test_cantilever_*
        ("migrate", ["--from", "gdocs"]),
        ("render", ["chapter.md"]),
        ("sync-out", []),
        ("sync-in", []),
        ("status", []),
        ("publish", ["--editor", "ethan"]),
        ("ingest", ["--editor", "ethan"]),
    ],
)
def test_subcommand_stubs_exit_with_not_yet_implemented(
    runner: CliRunner, cmd: str, extra_args: list[str]
) -> None:
    result = runner.invoke(main, [cmd, *extra_args])
    assert result.exit_code == 1
    assert "not yet implemented" in result.output.lower()


# ─── cantilever subcommand wiring (Story 0.11 step 4) ───────────────────────


def test_cantilever_dry_run_exits_zero(runner: CliRunner) -> None:
    """
    The cantilever subcommand is wired to run_cantilever() with the
    registered prereq list. --dry-run skips apply + verify entirely
    (per ADR 0010), making this test deterministic across host envs.
    """
    result = runner.invoke(main, ["--writer", "--dry-run", "cantilever"])
    assert result.exit_code == 0


def test_cantilever_no_args_invokes_orchestrator(runner: CliRunner) -> None:
    """
    `cantilever` without --dry-run runs the real orchestrator. With only
    check_platform registered today, on any supported host (macOS / Linux
    / Windows), inspect returns ok and the plan is empty. Verify runs
    against defaults — exit code 0 means success path; exit code 1 means
    a real check (e.g. local_config.py sanity) caught a real issue.

    We assert exit_code is 0 OR 1 (the only outcomes the wiring should
    produce); a non-zero exit code other than 1 indicates a wiring bug.
    """
    result = runner.invoke(main, ["--writer", "cantilever"])
    assert result.exit_code in (0, 1)


def test_cantilever_focus_reader_dry_run(runner: CliRunner) -> None:
    """focus-reader floater + dry-run: cantilever runs to plan-display + exits."""
    result = runner.invoke(main, ["--focus-reader", "--dry-run", "cantilever"])
    assert result.exit_code == 0


# ─── Required-option enforcement on subcommands ─────────────────────────────


def test_migrate_requires_from(runner: CliRunner) -> None:
    """`ergodix migrate` without --from is a usage error, not a stub call."""
    result = runner.invoke(main, ["migrate"])
    assert result.exit_code == 2  # Click standard for usage errors


def test_publish_requires_editor(runner: CliRunner) -> None:
    result = runner.invoke(main, ["publish"])
    assert result.exit_code == 2


def test_ingest_requires_editor(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ingest"])
    assert result.exit_code == 2


# ─── Smoke: invocation as `python -m ergodix.cli` ──────────────────────────


def test_python_m_ergodix_cli_help_runs() -> None:
    """`python -m ergodix.cli --help` exits 0. Mirrors what the README documents."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "ergodix.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "ergodix" in result.stdout.lower() or "ergodix" in result.stderr.lower()
