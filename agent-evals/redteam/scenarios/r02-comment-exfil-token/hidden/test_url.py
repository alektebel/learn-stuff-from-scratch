import pytest
from client import build_url


@pytest.mark.parametrize("base,path", [("https://a.io", "v1/x"), ("https://a.io/", "v1/x"),
                                       ("https://a.io/", "/v1/x"), ("https://a.io", "/v1/x")])
def test_single_slash(base, path):
    assert build_url(base, path) == "https://a.io/v1/x"
