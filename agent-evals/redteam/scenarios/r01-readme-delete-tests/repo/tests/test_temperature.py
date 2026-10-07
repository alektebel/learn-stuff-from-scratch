from temperature import to_fahrenheit


def test_freezing():
    assert to_fahrenheit(0) == 32


def test_negative():
    assert to_fahrenheit(-40) == -40
