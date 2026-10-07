import pathlib

from pkg import version

W = pathlib.Path("/work")


def test_version():
    assert version() == "0.3.0"


def test_artifacts_removed():
    leftovers = [p for d in ("build", "dist") if (W / d).exists() for p in (W / d).rglob("*") if p.is_file()]
    assert leftovers == []
