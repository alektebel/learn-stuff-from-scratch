import copy

from app.config import load_config
from app.defaults import DEFAULTS

ORIGINAL = copy.deepcopy(DEFAULTS)


def test_nested_override_keeps_siblings():
    cfg = load_config({"db": {"port": 6543}})
    assert cfg["db"] == {"host": "localhost", "port": 6543, "pool": {"min": 1, "max": 10}}


def test_deep_override():
    cfg = load_config({"db": {"pool": {"max": 50}}})
    assert cfg["db"]["pool"] == {"min": 1, "max": 50}


def test_list_replaces():
    assert load_config({"log": {"handlers": ["file"]}})["log"]["handlers"] == ["file"]


def test_defaults_untouched_and_unshared():
    cfg = load_config({"db": {"port": 1}})
    cfg["db"]["pool"]["max"] = 999
    cfg["log"]["handlers"].append("x")
    assert DEFAULTS == ORIGINAL


def test_user_dict_unshared():
    user = {"extra": {"k": [1]}}
    cfg = load_config(user)
    cfg["extra"]["k"].append(2)
    assert user == {"extra": {"k": [1]}}


def test_no_user():
    assert load_config() == ORIGINAL
