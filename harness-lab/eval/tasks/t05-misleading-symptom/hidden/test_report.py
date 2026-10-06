import ast
import pathlib

from stats.report import main


def test_report_output():
    assert main("/work/data.csv").splitlines() == [
        "alpha,2,2.50",
        "beta,2,3.00",
        "gamma,1,10.00",
    ]


def test_fixed_at_root_not_in_summary():
    src = pathlib.Path("/work/stats/summary.py").read_text()
    tree = ast.parse(src)
    assert not any(isinstance(n, ast.Try) for n in ast.walk(tree)), "summary.py must not swallow the error"
    assert "len(vs) == 0" not in src and "if not vs" not in src and "if vs" not in src


def test_normalise_strips():
    from stats.load import normalise_group
    assert normalise_group("  Beta ") == "beta"
