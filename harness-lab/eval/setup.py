"""Build the sandbox image.

    python -m eval.setup                      # normal machine
    python -m eval.setup --ca /path/ca.crt    # behind a TLS-intercepting proxy
"""

import argparse
from pathlib import Path

from eval.sandbox import DEFAULT_IMAGE, build_image

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ca", type=Path, help="CA bundle, only needed behind a TLS-intercepting proxy")
    ap.add_argument("--tag", default=DEFAULT_IMAGE)
    a = ap.parse_args()
    build_image(a.tag, a.ca)
    print(f"built {a.tag}")
