import pathlib
import warnings

import pytest
from geo.distance import calc_dist, haversine_km
from geo.nearest import nearest, within
from geo.route import route_length

MAD, BCN, PAR = (40.4168, -3.7038), (41.3874, 2.1686), (48.8566, 2.3522)


def test_value():
    assert haversine_km(MAD, BCN) == pytest.approx(505, abs=2)


def test_alias_warns_once_per_call():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert calc_dist(MAD, BCN) == haversine_km(MAD, BCN)
        calc_dist(MAD, PAR)
    dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(dep) == 2 and "haversine_km" in str(dep[0].message)


def test_package_does_not_use_alias():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert route_length([MAD, BCN, PAR]) > 1300
        assert nearest(MAD, [PAR, BCN]) == BCN
        assert within(MAD, [PAR, BCN], 600) == [BCN]
    for f in ["route.py", "nearest.py"]:
        assert "calc_dist" not in pathlib.Path("/work/geo", f).read_text()
