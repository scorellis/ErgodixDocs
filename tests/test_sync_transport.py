"""
Tests for ergodix.sync_transport — the auto-detection helper from
ADR 0014. Classifies a corpus folder's location into one of three
modes: drive-mirror, drive-stream, indy.

Detection is path-structure based — the function inspects the absolute
path's prefix without requiring the path to exist. Existence checking
is B2's job; this helper just classifies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ─── detect_sync_transport ─────────────────────────────────────────────────


def test_drive_mirror_path_returns_drive_mirror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path under ~/My Drive/... is classified as drive-mirror."""
    from ergodix.sync_transport import detect_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))
    corpus = tmp_path / "My Drive" / "MyOpus"

    assert detect_sync_transport(corpus) == "drive-mirror"


def test_my_drive_root_itself_is_drive_mirror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Drive mount root itself counts as drive-mirror — pinning the
    edge case where corpus is configured at the very top of My Drive."""
    from ergodix.sync_transport import detect_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))

    assert detect_sync_transport(tmp_path / "My Drive") == "drive-mirror"


def test_drive_stream_path_returns_drive_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path under ~/Library/CloudStorage/GoogleDrive-* is drive-stream."""
    from ergodix.sync_transport import detect_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))
    corpus = (
        tmp_path
        / "Library"
        / "CloudStorage"
        / "GoogleDrive-author@example.com"
        / "My Drive"
        / "MyOpus"
    )

    assert detect_sync_transport(corpus) == "drive-stream"


def test_local_path_in_documents_returns_indy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path anywhere in ~/Documents/ (or other home subdirectories that
    aren't Drive-related) classifies as indy — no sync transport."""
    from ergodix.sync_transport import detect_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))
    corpus = tmp_path / "Documents" / "MyOpus"

    assert detect_sync_transport(corpus) == "indy"


def test_path_outside_home_returns_indy() -> None:
    """A path entirely outside the user's home is indy. Pins that the
    detector doesn't accidentally classify e.g. an arbitrary absolute
    path as something sync-y."""
    from ergodix.sync_transport import detect_sync_transport

    assert detect_sync_transport(Path("/Users/_someone_else/Docs/MyOpus")) == "indy"


def test_other_cloudstorage_provider_is_indy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only GoogleDrive-* under CloudStorage triggers drive-stream — iCloud,
    Dropbox, OneDrive, etc. are all classified as indy. The user opted
    into a non-Drive sync setup; we don't pretend to support those in v1."""
    from ergodix.sync_transport import detect_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))
    icloud_corpus = tmp_path / "Library" / "CloudStorage" / "iCloud Drive" / "MyOpus"

    assert detect_sync_transport(icloud_corpus) == "indy"


def test_none_returns_drive_mirror_safe_default() -> None:
    """When CORPUS_FOLDER isn't configured (local_config.py missing or
    field not set), detector returns drive-mirror as a safe default —
    B1 will install Drive Desktop, B2 will surface the "not configured"
    failure with a clear remediation. Indy users edit local_config.py
    and re-run; their 30 seconds of unnecessary Drive install is
    cheaper than us guessing wrong about their setup."""
    from ergodix.sync_transport import detect_sync_transport

    assert detect_sync_transport(None) == "drive-mirror"


def test_relative_path_with_tilde_is_expanded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defensive: if a Path object happens to carry a ~ component (e.g.
    Path('~/My Drive/X') without expanduser), the detector handles it.
    In practice local_config.py uses Path.home() so this doesn't fire,
    but pinning the contract guards against a footgun."""
    from ergodix.sync_transport import detect_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))

    assert detect_sync_transport(Path("~/My Drive/MyOpus")) == "drive-mirror"


# ─── read_corpus_folder_from_local_config ─────────────────────────────────


def test_read_corpus_folder_returns_none_when_local_config_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.sync_transport import read_corpus_folder_from_local_config

    monkeypatch.chdir(tmp_path)

    assert read_corpus_folder_from_local_config() is None


def test_read_corpus_folder_returns_configured_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ergodix.sync_transport import read_corpus_folder_from_local_config

    config = tmp_path / "local_config.py"
    config.write_text(
        "from pathlib import Path\nCORPUS_FOLDER = Path('/Users/me/Documents/MyOpus')\n"
    )
    monkeypatch.chdir(tmp_path)

    result = read_corpus_folder_from_local_config()
    assert result == Path("/Users/me/Documents/MyOpus")


def test_read_corpus_folder_returns_none_when_field_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """local_config.py exists but doesn't define CORPUS_FOLDER → None.
    Doesn't crash; downstream callers can treat None as 'not yet
    configured' and act accordingly."""
    from ergodix.sync_transport import read_corpus_folder_from_local_config

    config = tmp_path / "local_config.py"
    config.write_text("OTHER_FIELD = 'something'\n")
    monkeypatch.chdir(tmp_path)

    assert read_corpus_folder_from_local_config() is None


def test_read_corpus_folder_returns_none_when_local_config_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed local_config.py (syntax error, ImportError, etc.) → None.
    The reader is not in the business of validating the file; that's
    the verify phase's job. Returning None lets callers fall back to
    safe defaults without crashing."""
    from ergodix.sync_transport import read_corpus_folder_from_local_config

    config = tmp_path / "local_config.py"
    config.write_text("import nonexistent_module_xyz\n")
    monkeypatch.chdir(tmp_path)

    assert read_corpus_folder_from_local_config() is None


# ─── detect_current_sync_transport — convenience ─────────────────────────


def test_detect_current_returns_drive_mirror_when_no_local_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No local_config.py → safe-default drive-mirror behavior, end to end."""
    from ergodix.sync_transport import detect_current_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    assert detect_current_sync_transport() == "drive-mirror"


def test_detect_current_returns_indy_with_local_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: local_config.py points at a Documents path → indy."""
    from ergodix.sync_transport import detect_current_sync_transport

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "local_config.py"
    config.write_text(
        f"from pathlib import Path\nCORPUS_FOLDER = Path('{tmp_path / 'Documents' / 'MyOpus'}')\n"
    )

    assert detect_current_sync_transport() == "indy"
