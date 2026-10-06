import json

import pytest
from contacts.cli import main
from contacts.store import Store
from contacts.validate import clean_phone


def test_clean_phone():
    assert clean_phone("+34 600-123 456") == "+34600123456"
    assert clean_phone(None) is None
    for bad in ["600123456", "+1234567", "+1234567890123456", "+34 6OO 123 456"]:
        with pytest.raises(ValueError):
            clean_phone(bad)


def test_cli_roundtrip(tmp_path, capsys):
    db = str(tmp_path / "c.json")
    assert main(["--db", db, "add", "Ana", "ana@x.io", "--phone", "+34 600 123 456"]) == 0
    assert main(["--db", db, "add", "Bob", "bob@x.io"]) == 0
    capsys.readouterr()
    main(["--db", db, "show", "Ana"])
    assert capsys.readouterr().out.splitlines() == ["name: Ana", "email: ana@x.io", "phone: +34600123456"]
    main(["--db", db, "show", "Bob"])
    assert capsys.readouterr().out.splitlines() == ["name: Bob", "email: bob@x.io"]
    main(["--db", db, "export"])
    assert capsys.readouterr().out.splitlines() == ["name,email,phone", "Ana,ana@x.io,+34600123456", "Bob,bob@x.io,"]


def test_invalid_phone_rejected_before_saving(tmp_path):
    store = Store(tmp_path / "c.json")
    with pytest.raises(ValueError):
        store.add("Ana", "ana@x.io", "12")
    assert store.all() == []


def test_legacy_records_load(tmp_path):
    p = tmp_path / "old.json"
    p.write_text(json.dumps([{"name": "Old", "email": "old@x.io"}]))
    (c,) = Store(p).all()
    assert c.phone is None
