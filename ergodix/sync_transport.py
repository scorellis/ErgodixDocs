"""
Sync transport detection (per ADR 0014).

Classifies a corpus folder's location into one of three modes:

- ``drive-mirror`` — corpus lives under Google Drive's Mirror mount
  (``~/My Drive/...``).
- ``drive-stream`` — corpus lives under Drive's Stream mount
  (``~/Library/CloudStorage/GoogleDrive-*/...``). Refused in v1; B2
  surfaces a "switch to Mirror" remediation.
- ``indy`` — corpus lives anywhere else on local disk; no Drive sync.
  First-class peer of drive-mirror in v1.

Detection is **path-structure based** — the function inspects the
absolute path's prefix without requiring the path to exist. Existence
checking is B2's job; this helper just classifies. That separation
matters because a freshly-installed user with `<YOUR-CORPUS-FOLDER>`
still in their `local_config.py` has a syntactically-valid path that
doesn't resolve to anything; the detector can still classify it as
drive-mirror (because it's structurally under My Drive) so B1 installs
Drive Desktop, and the verify phase later catches the placeholder
problem with its own remediation.

Convenience helper ``detect_current_sync_transport()`` chains the
local_config read + classification — most callers just want the
current mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

SyncMode = Literal["drive-mirror", "drive-stream", "indy"]


_MIRROR_DIR_NAME = "My Drive"
_STREAM_PARENT_PARTS = ("Library", "CloudStorage")
_STREAM_DIR_PREFIX = "GoogleDrive-"


def detect_sync_transport(corpus_folder: Path | None) -> SyncMode:
    """Classify the corpus folder's sync transport.

    ``None`` (no path provided — local_config missing or CORPUS_FOLDER
    unset) returns ``drive-mirror`` as a safe default. The downstream
    verify check / B2 will catch the missing-config case with its own
    remediation; classifying as drive-mirror here means B1 will
    optimistically install Drive Desktop, which is the conservative
    choice when we don't yet know the user's intent.
    """
    if corpus_folder is None:
        return "drive-mirror"

    home = Path.home()
    abs_path = Path(corpus_folder).expanduser()

    # Drive-mirror: under ~/My Drive (including the root itself).
    mirror_root = home / _MIRROR_DIR_NAME
    try:
        abs_path.relative_to(mirror_root)
        return "drive-mirror"
    except ValueError:
        pass

    # Drive-stream: under ~/Library/CloudStorage/GoogleDrive-*
    cloudstorage = home / _STREAM_PARENT_PARTS[0] / _STREAM_PARENT_PARTS[1]
    try:
        rel = abs_path.relative_to(cloudstorage)
        first_segment = rel.parts[0] if rel.parts else ""
        if first_segment.startswith(_STREAM_DIR_PREFIX):
            return "drive-stream"
    except ValueError:
        pass

    return "indy"


def read_corpus_folder_from_local_config() -> Path | None:
    """Read ``CORPUS_FOLDER`` from ``local_config.py`` at the current
    working directory. Returns ``None`` if the file doesn't exist, the
    field isn't defined, or the import raises.

    Cantilever runs from the repo root, where ``local_config.py``
    lives. Tests use ``monkeypatch.chdir`` to point this at a fixture.

    This reader is intentionally *defensive* — its job is to surface
    a path or a None, not to validate the file. The
    ``_verify_local_config_sane`` smoke check is the loud-failure
    surface for malformed configs; this helper stays quiet so callers
    (B1, B2) can act on partial information without crashing.
    """
    config_path = Path.cwd() / "local_config.py"
    if not config_path.exists():
        return None

    import importlib.util

    spec = importlib.util.spec_from_file_location("_sync_transport_local_config", config_path)
    if spec is None or spec.loader is None:
        return None

    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        return None

    corpus = getattr(module, "CORPUS_FOLDER", None)
    if corpus is None:
        return None

    if isinstance(corpus, Path):
        return corpus
    if isinstance(corpus, str) and corpus:
        return Path(corpus)
    return None


def detect_current_sync_transport() -> SyncMode:
    """Convenience: read ``CORPUS_FOLDER`` from local_config.py and
    classify in one call. Most prereq callers want this rather than
    the two-step form."""
    return detect_sync_transport(read_corpus_folder_from_local_config())
