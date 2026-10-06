from versions import is_newer, latest


def test_numeric_not_lexical():
    assert is_newer("1.10.0", "1.9.0")


def test_release_beats_prerelease():
    assert is_newer("1.0.0", "1.0.0-rc.1")


def test_prerelease_numeric_identifiers():
    assert is_newer("1.0.0-rc.10", "1.0.0-rc.2")


def test_latest():
    assert latest(["1.0.0-beta", "1.0.0-alpha.1", "0.9.9", "1.0.0-alpha"]) == "1.0.0-beta"
