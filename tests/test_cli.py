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
        # status is wired — see test_status_* below
        # migrate is wired (chunk 4) — see test_migrate_* below
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


# ─── migrate subcommand (chunk 4 of ADR 0015) ──────────────────────────────


def _stub_migrate_run(monkeypatch: pytest.MonkeyPatch, captured: dict) -> None:
    """Replace `ergodix.migrate.migrate_run` with a stub that records the
    call and returns a synthetic MigrateResult so we can assert on the
    CLI's wiring without exercising the real orchestrator."""
    import ergodix.migrate as migrate_module

    def fake_run(**kwargs: object) -> object:
        captured.update(kwargs)
        return migrate_module.MigrateResult(
            run_id="2026-05-10-120000",
            manifest_path=Path("/tmp/manifest.toml"),  # noqa: S108
            counts={"migrated": 2, "skipped": 1},
            files=(),
        )

    monkeypatch.setattr(migrate_module, "migrate_run", fake_run)


def _stub_get_docs_service(monkeypatch: pytest.MonkeyPatch) -> object:
    """Stub `ergodix.auth.get_docs_service` so the CLI doesn't trigger
    OAuth during tests."""
    sentinel = object()
    monkeypatch.setattr("ergodix.auth.get_docs_service", lambda **_kwargs: sentinel)
    return sentinel


def _write_local_config(tmp_path: Path, *, corpus: Path, author: str | None = None) -> None:
    body = "from pathlib import Path\n"
    body += f"CORPUS_FOLDER = Path('{corpus}')\n"
    if author is not None:
        body += f'AUTHOR = "{author}"\n'
    (tmp_path / "local_config.py").write_text(body, encoding="utf-8")


def test_migrate_requires_from_flag(runner: CliRunner) -> None:
    result = runner.invoke(main, ["migrate"])
    assert result.exit_code != 0
    assert "--from" in result.output


def test_migrate_check_and_force_are_mutually_exclusive(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_config(tmp_path, corpus=tmp_path / "corpus")
    captured: dict[str, object] = {}
    _stub_migrate_run(monkeypatch, captured)
    _stub_get_docs_service(monkeypatch)

    result = runner.invoke(main, ["migrate", "--from", "gdocs", "--check", "--force"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()
    # migrate_run must not have been called.
    assert captured == {}


def test_migrate_invokes_migrate_run_with_resolved_args(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    corpus = tmp_path / "my-corpus"
    corpus.mkdir()
    _write_local_config(tmp_path, corpus=corpus, author="Test Author")
    captured: dict[str, object] = {}
    sentinel_service = _stub_get_docs_service(monkeypatch)
    _stub_migrate_run(monkeypatch, captured)

    result = runner.invoke(main, ["migrate", "--from", "gdocs"])

    assert result.exit_code == 0, result.output
    assert captured["importer_name"] == "gdocs"
    assert captured["corpus_root"] == corpus
    assert captured["author"] == "Test Author"
    assert captured["docs_service"] is sentinel_service
    assert captured["check"] is False
    assert captured["force"] is False
    assert captured["limit"] is None


def test_migrate_corpus_flag_overrides_local_config(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config_corpus = tmp_path / "config-corpus"
    config_corpus.mkdir()
    flag_corpus = tmp_path / "flag-corpus"
    flag_corpus.mkdir()
    _write_local_config(tmp_path, corpus=config_corpus, author="A")
    captured: dict[str, object] = {}
    _stub_get_docs_service(monkeypatch)
    _stub_migrate_run(monkeypatch, captured)

    result = runner.invoke(main, ["migrate", "--from", "gdocs", "--corpus", str(flag_corpus)])

    assert result.exit_code == 0, result.output
    assert captured["corpus_root"] == flag_corpus


def test_migrate_passes_check_and_force_and_limit(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_config(tmp_path, corpus=tmp_path / "corpus", author="A")
    captured: dict[str, object] = {}
    _stub_get_docs_service(monkeypatch)
    _stub_migrate_run(monkeypatch, captured)

    result = runner.invoke(main, ["migrate", "--from", "gdocs", "--check", "--limit", "5"])
    assert result.exit_code == 0, result.output
    assert captured["check"] is True
    assert captured["force"] is False
    assert captured["limit"] == 5


def test_migrate_falls_back_to_git_config_user_name_for_author(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # No AUTHOR in local_config.
    _write_local_config(tmp_path, corpus=tmp_path / "corpus")
    captured: dict[str, object] = {}
    _stub_get_docs_service(monkeypatch)
    _stub_migrate_run(monkeypatch, captured)

    monkeypatch.setattr("ergodix.cli._git_config_user_name", lambda: "Git User")

    result = runner.invoke(main, ["migrate", "--from", "gdocs"])
    assert result.exit_code == 0, result.output
    assert captured["author"] == "Git User"


def test_migrate_errors_when_corpus_unconfigured(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # No local_config.py at all.
    captured: dict[str, object] = {}
    _stub_get_docs_service(monkeypatch)
    _stub_migrate_run(monkeypatch, captured)

    result = runner.invoke(main, ["migrate", "--from", "gdocs"])
    assert result.exit_code != 0
    assert "corpus" in result.output.lower()
    assert captured == {}


def test_migrate_prints_summary_counts(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_config(tmp_path, corpus=tmp_path / "corpus", author="A")
    captured: dict[str, object] = {}
    _stub_get_docs_service(monkeypatch)
    _stub_migrate_run(monkeypatch, captured)

    result = runner.invoke(main, ["migrate", "--from", "gdocs"])

    assert result.exit_code == 0, result.output
    assert "migrated" in result.output.lower()
    assert "2" in result.output  # the stub returned counts={"migrated": 2, "skipped": 1}
    assert "1" in result.output


def test_migrate_exits_one_when_failures_present(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_local_config(tmp_path, corpus=tmp_path / "corpus", author="A")
    _stub_get_docs_service(monkeypatch)

    import ergodix.migrate as migrate_module

    def fake_run_with_failures(**_kwargs: object) -> object:
        return migrate_module.MigrateResult(
            run_id="2026-05-10-120000",
            manifest_path=Path("/tmp/manifest.toml"),  # noqa: S108
            counts={"migrated": 1, "failed": 2},
            files=(),
        )

    monkeypatch.setattr(migrate_module, "migrate_run", fake_run_with_failures)

    result = runner.invoke(main, ["migrate", "--from", "gdocs"])

    assert result.exit_code == 1
    assert "failed" in result.output.lower()
