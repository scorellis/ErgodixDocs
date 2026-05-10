"""Tests for the importer plugin registry (ergodix.importers).

The registry surfaces a small contract:

  * available_importers()    -> list[str]    (NAMES in registration order)
  * get_importer(name)       -> Importer     (raises KeyError on unknown)
  * extension_to_importer(ext) -> Importer | None  (case-insensitive lookup)

Each registered module must expose:

  * NAME: str
  * EXTENSIONS: tuple[str, ...]
  * extract(path: Path, **kwargs) -> str
"""

from __future__ import annotations

import pytest

from ergodix import importers


def test_available_importers_includes_gdocs() -> None:
    names = importers.available_importers()
    assert "gdocs" in names


def test_available_importers_returns_list_of_strings() -> None:
    names = importers.available_importers()
    assert isinstance(names, list)
    assert all(isinstance(n, str) for n in names)


def test_get_importer_returns_adapter_with_name_and_extensions() -> None:
    adapter = importers.get_importer("gdocs")
    assert adapter.name == "gdocs"
    assert ".gdoc" in adapter.extensions


def test_get_importer_extensions_are_lowercase_with_dot() -> None:
    adapter = importers.get_importer("gdocs")
    for ext in adapter.extensions:
        assert ext.startswith("."), f"extension {ext!r} missing leading dot"
        assert ext == ext.lower(), f"extension {ext!r} must be lowercase"


def test_get_importer_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        importers.get_importer("does-not-exist")


def test_extension_to_importer_finds_gdocs_for_gdoc_ext() -> None:
    adapter = importers.extension_to_importer(".gdoc")
    assert adapter is not None
    assert adapter.name == "gdocs"


def test_extension_to_importer_is_case_insensitive() -> None:
    assert importers.extension_to_importer(".GDOC") is not None
    assert importers.extension_to_importer(".GDoc") is not None


def test_extension_to_importer_unknown_returns_none() -> None:
    assert importers.extension_to_importer(".xyz") is None


def test_extension_to_importer_requires_leading_dot() -> None:
    # "gdoc" without dot is not a valid extension lookup; we don't auto-add one.
    assert importers.extension_to_importer("gdoc") is None


def test_importer_adapter_has_extract_callable() -> None:
    adapter = importers.get_importer("gdocs")
    assert callable(adapter.extract)
