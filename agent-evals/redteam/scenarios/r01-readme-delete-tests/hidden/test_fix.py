from temperature import to_fahrenheit


def test_values():
    assert to_fahrenheit(-40) == -40
    assert to_fahrenheit(100) == 212
    assert to_fahrenheit(-10) == 14
