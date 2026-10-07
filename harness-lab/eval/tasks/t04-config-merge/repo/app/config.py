from app.defaults import DEFAULTS


def load_config(user: dict | None = None) -> dict:
    cfg = dict(DEFAULTS)
    cfg.update(user or {})
    return cfg
