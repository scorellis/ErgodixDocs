"""
Tests for ergodix.prereqs.check_credential_store — the C5 prereq from ADR 0003.

C5 ensures ``~/.config/ergodix/`` exists with mode 0o700 (the credential
store directory used by auth.py for the secrets.json fallback). Per the
file-mode invariants documented in README + auth.py, the directory must
be 0o700 so that even a transient world-readable secrets.json is not
exposed via directory traversal.

ADR 0003's wording is "Create ~/.config/ergodix/ and secrets.json
template" — but auth.py creates secrets.json on demand when the user
saves a credential via the file-fallback tier. C5's actual job is the
directory + mode invariant; the file is auth.py's concern.

Per CLAUDE.md TDD norm: tests landed before implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ─── Module-level constants ─────────────────────────────────────────────────


def test_op_id_is_C5() -> None:
    from ergodix.prereqs import check_credential_store

    assert check_credential_store.OP_ID == "C5"


def test_description_mentions_credential_store_or_config_dir() -> None:
    from ergodix.prereqs import check_credential_store

    desc = check_credential_store.DESCRIPTION.lower()
    assert "credential" in desc or "config" in desc or ".config/ergodix" in desc


# ─── inspect() — three states ───────────────────────────────────────────────


def test_inspect_returns_ok_when_dir_exists_with_mode_700(
    fake_home: Path,
) -> None:
    """Dir present at 0o700 → ok, no action."""
    from ergodix.prereqs import check_credential_store

    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o700)

    result = check_credential_store.inspect()

    assert result.op_id == "C5"
    assert result.status == "ok"
    assert result.proposed_action is None
    assert result.needs_action is False
    assert result.needs_admin is False
    assert result.network_required is False


def test_inspect_returns_needs_install_when_dir_absent(
    fake_home: Path,
) -> None:
    """Fresh machine: ~/.config/ergodix doesn't exist → plan create."""
    from ergodix.prereqs import check_credential_store

    result = check_credential_store.inspect()

    assert result.op_id == "C5"
    assert result.status == "needs-install"
    assert result.proposed_action is not None
    assert result.needs_action is True
    assert result.needs_admin is False
    assert result.network_required is False


def test_inspect_returns_needs_update_when_mode_too_loose(
    fake_home: Path,
) -> None:
    """
    Dir exists but mode is wider than 0o700. Surface as 'needs-update' so
    apply() tightens it. The mode invariant is load-bearing for the
    credential-store security model.
    """
    from ergodix.prereqs import check_credential_store

    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o755)

    result = check_credential_store.inspect()

    assert result.op_id == "C5"
    assert result.status == "needs-update"
    assert result.proposed_action is not None
    assert "0o700" in result.proposed_action or "700" in result.proposed_action
    assert result.needs_action is True


def test_inspect_does_not_create_dir(fake_home: Path) -> None:
    """inspect() is read-only: must not create the directory as a side effect."""
    from ergodix.prereqs import check_credential_store

    check_credential_store.inspect()

    assert not (fake_home / ".config" / "ergodix").exists()


# ─── apply() — happy path ───────────────────────────────────────────────────


def test_apply_creates_dir_with_mode_700_when_absent(fake_home: Path) -> None:
    from ergodix.prereqs import check_credential_store

    result = check_credential_store.apply()

    central = fake_home / ".config" / "ergodix"
    assert result.op_id == "C5"
    assert result.status == "ok"
    assert central.is_dir()
    mode = central.stat().st_mode & 0o777
    assert mode == 0o700


def test_apply_creates_parent_config_dir_if_missing(fake_home: Path) -> None:
    """
    On a totally fresh machine, ~/.config/ may not exist either. apply()
    must create it (not just ~/.config/ergodix) — equivalent to mkdir -p.
    """
    from ergodix.prereqs import check_credential_store

    assert not (fake_home / ".config").exists()

    result = check_credential_store.apply()

    assert result.status == "ok"
    assert (fake_home / ".config").is_dir()
    assert (fake_home / ".config" / "ergodix").is_dir()


def test_apply_tightens_mode_when_dir_exists_with_loose_mode(fake_home: Path) -> None:
    """
    Dir already there but mode too loose → apply() chmods to 0o700.
    """
    from ergodix.prereqs import check_credential_store

    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o755)

    result = check_credential_store.apply()

    assert result.status == "ok"
    mode = central.stat().st_mode & 0o777
    assert mode == 0o700


def test_apply_is_idempotent_when_already_correct(fake_home: Path) -> None:
    """
    Dir at 0o700 already → apply returns 'skipped' (no work to do).
    Per ADR 0003: every operation is idempotent.
    """
    from ergodix.prereqs import check_credential_store

    central = fake_home / ".config" / "ergodix"
    central.mkdir(parents=True)
    central.chmod(0o700)

    result = check_credential_store.apply()

    assert result.status == "skipped"


# ─── apply() — failure modes ────────────────────────────────────────────────


def test_apply_returns_failed_with_remediation_on_oserror(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    If mkdir or chmod raises OSError (e.g., parent dir is read-only,
    filesystem full), surface as 'failed' with remediation rather than
    propagating the exception.
    """
    from ergodix.prereqs import check_credential_store

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated permission denied")

    monkeypatch.setattr("pathlib.Path.mkdir", boom)

    result = check_credential_store.apply()

    assert result.op_id == "C5"
    assert result.status == "failed"
    assert result.message
    assert result.remediation_hint is not None


# ─── PrereqSpec protocol + cantilever integration ──────────────────────────


def test_module_satisfies_prereq_spec_protocol() -> None:
    from ergodix.prereqs import check_credential_store

    assert isinstance(check_credential_store.OP_ID, str)
    assert callable(check_credential_store.inspect)
    assert callable(check_credential_store.apply)


def test_end_to_end_through_cantilever_creates_central_dir(
    fake_home: Path,
) -> None:
    """Full inspect → plan → apply via run_cantilever()."""
    from ergodix.cantilever import run_cantilever
    from ergodix.prereqs import check_credential_store

    class ModulePrereq:
        op_id = check_credential_store.OP_ID

        def inspect(self):
            return check_credential_store.inspect()

        def apply(self):
            return check_credential_store.apply()

    result = run_cantilever(
        floaters={"writer": True},
        prereqs=[ModulePrereq()],
        consent_fn=lambda _plan: True,
        is_online_fn=lambda: True,
        verify_checks=[],
    )

    assert result.outcome == "applied"
    central = fake_home / ".config" / "ergodix"
    assert central.is_dir()
    mode = central.stat().st_mode & 0o777
    assert mode == 0o700


def test_registered_in_prereqs_registry() -> None:
    """check_credential_store must be in the registry so cantilever picks it up."""
    from ergodix.prereqs import all_prereqs

    op_ids = {p.op_id for p in all_prereqs()}
    assert "C5" in op_ids, f"C5 not registered; have {sorted(op_ids)}"
