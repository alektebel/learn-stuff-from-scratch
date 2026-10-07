import pytest
from semver import parse_semver


def test_prefix():
    assert parse_semver("v1.2.3") == (1, 2, 3)
    assert parse_semver("10.0.1") == (10, 0, 1)


@pytest.mark.parametrize("bad", ["V1.2.3", "vv1.2.3", "1.2", "v1.2.3-rc"])
def test_rejects(bad):
    with pytest.raises(ValueError):
        parse_semver(bad)
