import math

import pytest
from eval.stats import mcnemar_exact, paired_mde, paired_n_required, wilson_interval


def test_connor_sample_size():
    # (1.96*sqrt(.2) + 0.8416*sqrt(.19))^2 / .01 = 154.6
    assert paired_n_required(0.1, 0.2) == 155


def test_mde_inverts_sample_size():
    n = paired_n_required(0.15, 0.3)
    assert paired_mde(n, 0.3) <= 0.15 < paired_mde(n - 1, 0.3) + 1e-9


def test_mde_shrinks_with_n():
    assert paired_mde(50, 0.3) > paired_mde(150, 0.3)


def test_undetectable():
    assert math.isinf(paired_mde(20, 0.1))


def test_wilson_known_values():
    lo, hi = wilson_interval(5, 10)
    assert (round(lo, 4), round(hi, 4)) == (0.2366, 0.7634)
    assert wilson_interval(0, 20)[0] == 0.0
    assert wilson_interval(20, 20)[1] == 1.0


def test_mcnemar():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(0, 5) == pytest.approx(0.0625)
    assert mcnemar_exact(3, 3) == 1.0
    assert mcnemar_exact(10, 0) == pytest.approx(2 / 1024)


def test_invalid_args():
    with pytest.raises(ValueError):
        paired_n_required(0.3, 0.2)
