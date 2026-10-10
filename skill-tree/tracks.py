"""Track registry and the gamification rules, shared by tree.py and render_html.py.

A *track* is one column of the map and one domain of the curriculum. Every track
has a `label`, a `color`, a `root` (the directory its deliverables live under) and a
`domain` (the group it belongs to for badges). Nodes stay `<track>-NN-slug`.

Gamification (medium): each node is worth XP by `difficulty` (1-5); a `kind =
"capstone"` node is a boss and doubles its XP; an `exists` node is already-built
material and is worth no XP until it earns graded checks. A *level* is a total-XP
threshold with a rank name. A track earns a *badge* when every one of its nodes is
built (XP or exists); a domain earns one when all its tracks are badged.
"""

from __future__ import annotations

from dataclasses import dataclass

XP_BY_DIFFICULTY = {1: 10, 2: 25, 3: 60, 4: 120, 5: 250}
CAPSTONE_MULTIPLIER = 2
DEFAULT_DIFFICULTY = 2

# (threshold, rank); the highest threshold reached wins.
LEVELS = (
    (0, "Novice"),
    (150, "Apprentice"),
    (400, "Practitioner"),
    (900, "Adept"),
    (1800, "Expert"),
    (3500, "Master"),
    (6500, "Grandmaster"),
)


@dataclass(frozen=True)
class Track:
    label: str
    color: str
    root: str          # deliverables live under "<root>/"
    domain: str        # grouping for badges


TRACKS: dict[str, Track] = {
    # mathematics
    "foundations":  Track("Foundations",        "#E0B33C", "math/foundations",  "mathematics"),
    "linalg":       Track("Linear algebra",      "#58B0A4", "math/linalg",       "mathematics"),
    "probability":  Track("Probability",         "#B48AD6", "math/probability",  "mathematics"),
    "optimization": Track("Optimisation",        "#E08A5A", "math/optimization", "mathematics"),
    "prml":         Track("Pattern recognition", "#8CBF68", "math/prml",         "mathematics"),
    "lean":         Track("Lean",                "#96A0B2", "math/lean",         "mathematics"),
    # systems
    "lowlevel":     Track("Low level",           "#7FB3D5", "lowlevel",          "systems"),
    "distributed":  Track("Distributed",         "#E5A15C", "distributed",       "systems"),
    "databases":    Track("Databases",           "#C58AF9", "databases",         "systems"),
    "security":     Track("Security",            "#E06C75", "security",          "systems"),
    "web":          Track("Web & protocols",     "#56B6C2", "web",               "systems"),
    "gpu":          Track("GPU & performance",   "#D19A66", "gpu",               "systems"),
    "langs":        Track("Languages",           "#B8A2D9", "langs",             "systems"),
    # cloud
    "cloud":        Track("Cloud / AWS",         "#FFB454", "cloud",             "cloud"),
    "deploy":       Track("Deploy & SRE",        "#61AFEF", "deploy",            "cloud"),
    # ai
    "mlsys":        Track("ML systems",          "#8CBF68", "mlsys",             "ai"),
    "llm":          Track("LLMs",                "#A3BE8C", "llm",               "ai"),
    "agents":       Track("Agents",              "#5C9CE6", "agents",            "ai"),
    "quant":        Track("Quant",               "#E0B33C", "quant",             "ai"),
    # craft
    "algos":        Track("Algorithms & craft",  "#8893A8", "algos",             "craft"),
}

DOMAIN_LABEL = {
    "mathematics": "Mathematics",
    "systems": "Systems",
    "cloud": "Cloud",
    "ai": "AI",
    "craft": "Craft",
}


def node_xp(node: dict) -> int:
    """XP a node is worth once built (0 for material that already exists without checks)."""
    if node.get("status") == "exists":
        return 0
    xp = XP_BY_DIFFICULTY.get(node.get("difficulty", DEFAULT_DIFFICULTY), XP_BY_DIFFICULTY[2])
    if node.get("kind") == "capstone":
        xp *= CAPSTONE_MULTIPLIER
    return xp


def earned_xp(nodes: list[dict]) -> int:
    return sum(node_xp(n) for n in nodes if n["status"] == "done")


def max_xp(nodes: list[dict]) -> int:
    return sum(node_xp(n) for n in nodes)


def level_for(xp: int) -> tuple[int, str, int | None]:
    """(level number, rank, XP needed for the next level or None)."""
    level = 1
    rank = LEVELS[0][1]
    nxt = None
    for i, (threshold, name) in enumerate(LEVELS):
        if xp >= threshold:
            level, rank = i + 1, name
            nxt = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else None
    return level, rank, nxt


def track_done(nodes: list[dict], track: str) -> bool:
    mem = [n for n in nodes if n["track"] == track]
    return bool(mem) and all(n["status"] in ("done", "exists") for n in mem)


def badges(nodes: list[dict]) -> dict:
    """{"tracks": {track: bool}, "domains": {domain: bool}}."""
    tracks = {t: track_done(nodes, t) for t in TRACKS if any(n["track"] == t for n in nodes)}
    domains: dict[str, bool] = {}
    for domain in dict.fromkeys(TRACKS[t].domain for t in tracks):
        member_tracks = [t for t in tracks if TRACKS[t].domain == domain]
        domains[domain] = bool(member_tracks) and all(tracks[t] for t in member_tracks)
    return {"tracks": tracks, "domains": domains}
