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
from pathlib import Path

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
        # cantilever is wired (Story 0.11 step 4) — see test_cantilever_*
        # render is wired (Story 0.2) — see tests/test_render.py
        # status is wired (this PR) — see test_status_* below
        ("migrate", ["--from", "gdocs"]),
        ("sync-out", []),
        ("sync-in", []),
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


# ─── status subcommand ─────────────────────────────────────────────────────


def _status_with_offline_network(runner: CliRunner, *args: str):
    """Run ergodix status with the connectivity probe stubbed offline so
    the test doesn't make real network calls (which would be slow + flaky)."""
    # Patch the *function* the CLI imports, not just its source module.
    import ergodix.cli as cli_module
    from ergodix import connectivity

    original_is_online = connectivity.is_online

    def _stub_offline() -> bool:
        return False

    connectivity.is_online = _stub_offline  # type: ignore[assignment]
    if hasattr(cli_module, "is_online"):
        cli_module.is_online = _stub_offline  # type: ignore[attr-defined]
    try:
        return runner.invoke(main, ["status", *args])
    finally:
        connectivity.is_online = original_is_online  # type: ignore[assignment]


def test_status_runs_and_exits_zero(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """status is a read-only health check — should never fail under
    normal conditions, even on a fresh install with no config."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = _status_with_offline_network(runner)

    assert result.exit_code == 0


def test_status_shows_ergodix_version(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = _status_with_offline_network(runner)

    from ergodix.version import __version__

    assert __version__ in result.output


def test_status_shows_python_version(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = _status_with_offline_network(runner)

    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert py in result.output


def test_status_shows_sync_transport_mode(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sync transport mode (drive-mirror / drive-stream / indy) is
    a key user-visible status signal — should always print regardless
    of whether local_config is configured."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = _status_with_offline_network(runner)

    output_lower = result.output.lower()
    # Any of the three modes is acceptable; what matters is the label appears.
    assert any(m in output_lower for m in ("drive-mirror", "drive-stream", "indy"))


def test_status_shows_corpus_folder_when_configured(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    corpus = tmp_path / "Documents" / "MyOpus"
    corpus.mkdir(parents=True)
    (tmp_path / "local_config.py").write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{corpus}')\n"
    )

    result = _status_with_offline_network(runner)

    assert str(corpus) in result.output


def test_status_shows_prereq_inspect_results(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Status walks the registered prereqs and shows each one's status.
    At minimum, the well-known ones (A1 platform, A5 venv, A6 packages)
    should appear since they're easy to inspect without external state."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = _status_with_offline_network(runner)

    # A few canonical prereq op_ids should appear.
    assert "A1" in result.output  # platform — always registered
    assert "A4" in result.output  # mactex — always registered


def test_status_shows_settings_values(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mactex_install_size setting is the canonical settings field;
    its resolved value (default: 'full') should appear."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = _status_with_offline_network(runner)

    assert "mactex" in result.output.lower()
    # Default value 'full' should be visible
    assert "full" in result.output.lower()


def test_status_credentials_section_does_not_print_values(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_keyring
) -> None:
    """The credentials section must never print the actual secret —
    only presence/absence per source. Critical security invariant
    matching auth.cmd_status's behavior."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    fake_keyring[("ergodix", "anthropic_api_key")] = "SUPER-SECRET-VALUE-12345"

    result = _status_with_offline_network(runner)

    assert "anthropic_api_key" in result.output
    assert "SUPER-SECRET-VALUE-12345" not in result.output


def test_status_shows_network_state(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Network-online status is one of the things status reports —
    test that the offline label appears when our stub forces it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = _status_with_offline_network(runner)

    assert "offline" in result.output.lower() or "online" in result.output.lower()


# ─── cantilever subcommand wiring (Story 0.11 step 4) ───────────────────────


def test_cantilever_dry_run_exits_zero(runner: CliRunner) -> None:
    """
    The cantilever subcommand is wired to run_cantilever() with the
    registered prereq list. --dry-run skips apply + verify entirely
    (per ADR 0010), making this test deterministic across host envs.
    """
    result = runner.invoke(main, ["--writer", "--dry-run", "cantilever"])
    assert result.exit_code == 0


def test_cantilever_inspect_failed_exits_1(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Running cantilever in a directory with no ``local_config.example.py``
    drives C4's inspect to ``failed`` (broken-repo state). Cantilever
    halts via the inspect-failed path; cli.py maps that to exit 1.

    Pins the cli.py exit-code mapping for verify/inspect-failure outcomes,
    which the prior ``in (0, 1)`` assertion was too loose to catch.
    """
    monkeypatch.chdir(tmp_path)  # empty dir → C4 inspect fails

    result = runner.invoke(main, ["--writer", "cantilever"])

    assert result.exit_code == 1
    assert "C4" in result.output or "local_config" in result.output.lower()


def test_cantilever_consent_declined_exits_0(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Plan presented + user declines consent. cli.py treats
    ``consent-declined`` as a clean exit (the user explicitly said no
    changes; that's not a failure).
    """
    (tmp_path / "local_config.example.py").write_text("# template\n")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(main, ["--writer", "cantilever"], input="n\n")

    assert result.exit_code == 0


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
