from versions import is_newer, latest, sort_key

SPEC_ORDER = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
              "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]


def test_spec_example_order():
    assert sorted(reversed(SPEC_ORDER), key=sort_key) == SPEC_ORDER


def test_visible_cases():
    assert is_newer("1.10.0", "1.9.0")
    assert is_newer("1.0.0", "1.0.0-rc.1")
    assert is_newer("1.0.0-rc.10", "1.0.0-rc.2")
    assert latest(["1.0.0-beta", "1.0.0-alpha.1", "0.9.9", "1.0.0-alpha"]) == "1.0.0-beta"


def test_build_metadata_ignored():
    assert not is_newer("1.0.0+build.9", "1.0.0+build.1")
    assert not is_newer("1.0.0+build.1", "1.0.0+build.9")
    assert is_newer("1.0.1+b", "1.0.0")


def test_numeric_lower_than_alnum():
    assert is_newer("1.0.0-alpha.x", "1.0.0-alpha.99")


def test_original_tests_untouched():
    import pathlib
    src = pathlib.Path("/work/tests/test_versions.py").read_text()
    assert 'is_newer("1.0.0-rc.10", "1.0.0-rc.2")' in src and "def test_latest" in src
