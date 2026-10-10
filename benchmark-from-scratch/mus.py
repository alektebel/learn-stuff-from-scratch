"""mus.py — the PROVIDED mus domain. Do not edit; it has no TODOs.

The course grades the machinery AROUND a decision: turn gating, decision
records, retries, determinism, scorecards, calibration, paired tournaments.
That machinery needs a game that is real enough to be worth measuring and small
enough to hold in your head. Mus is that game. This module is the engine, two
reference policies and the truth oracles — and nothing else: no model, no
network, no record writer, no scorecard, no señas.

Five things this file exists to get exactly right, because a benchmark that
gets any of them wrong reports numbers that cannot be reproduced:

  1. Two independent RNG streams. `deal_seed` (or `seed`) drives the shuffles
     that deal, through its own `random.Random`, advanced by `deal()` and by
     nothing else; a second stream drives the reshuffles that a mus discard
     causes. So the sequence of DEALS is a function of the seed alone: two runs
     that play completely differently still hold the same cards. That is what
     makes paired tournaments possible.
  2. No module-level mutable state. Two `Table`s in one process cannot touch
     each other. (The one module-level dict below is a write-once cache of a
     pure function of the rules, not state.)
  3. `apply` is atomic. The seat, the action name and the payload are all
     validated before one field changes, so a refused action is invisible.
  4. Policies own their own `random.Random(seed)`. Nothing here touches the
     global `random`, so a seeded run reproduces in any process.
  5. `self_play` is a pure function of (seed, policies, hands): same inputs,
     same JSON.

The rules, from the reference engine (mus-benchmark/src/musbench/mus/engine.py)
with the simplification this course asked for:

  * Teams are {0: 0, 1: 1, 2: 0, 3: 1}; the mano seat rotates every hand.
  * Points: rey, caballo, sota and tres are 10; as and dos are 1; 4-7 natural.
  * Grande: tres counts as rey (both 12, the top), then caballo, sota, 7..4,
    and dos (2) beats as (1). Best card first, then second, and so on.
  * Chica: the same order reversed in spirit — as (11) is best, dos (10),
    tres/rey (9), cuatro (8), ... caballo (1) worst.
  * Pares: only tres=rey; as+dos is NOT a pair. duples (3) > medias (2) >
    par (1), four of a kind is a duples of its own (mus-)rank.
  * Juego: a total of 31-40; 31 is strongest, then 32, 40, 39 ... 33. A hand
    under 31 is not a juego — it is a punto, and loses to any juego.
  * Grande and Chica are worth 1 piedra. Pares and Juego are worth what the
    winning team's hands are worth (1-3 each; the reference sums them, and so
    does this port — a lance can therefore pay more than 3).
  * 40 piedras = 1 vaca; when a vaca lands BOTH point counters go back to 0
    (and the per-hand gains do NOT — they are what the hand won).
  * Phases: MUS_REQUEST (any 'no' skips the discards for everyone) -> MUS_DRAW
    (1-4 cards) -> up to `mus_rounds` request rounds -> per lance: DECLARE
    (truthful tengo/no-tengo for Pares and Juego) -> ENVITE (paso, envido,
    y-yo, reenvido, ordago, quiero, no-quiero, with raises capped by
    `envite_max`) -> ORDAGO_RESPONSE -> the next lance -> DONE.

Frozen surface later stages import:

    constants    PALOS RANKS CARD_POINTS RANK_GRANDE RANK_CHICA JUEGO_RANK
                 JUEGO_TOTALS TEAM_OF VACA_TARGET TURN_LIMIT LANCE_NAMES
    errors       IllegalAction, TurnLimitExceeded
    phase        Phase
    deck         Card, make_deck
    table        Table(seed=, deal_seed=, mus_rounds=, envite_max=)
    oracles      team_of(seat)  strength(table, seat, lance=None)
                 lance_winner(table, lance=None)  would_win(table, seat, lance=None)
                 default_action(table, seat)
    policies     random_policy(seed)  heuristic_policy(seed)
    match        self_play(seed, hands=, policies=, record_deals=)

A lance name is "grande", "chica", "pares", "juego" or "punto" (case
insensitive); `None` means "the lance the table is playing now", and outside
the lances — during the mus phase, or once the hand is DONE — there is no lance
to answer for, so the three oracles return None rather than a number no seat
could act on.

DESIGN DECISION — two RNG streams, not one.
    A single stream makes the deals depend on the play: a discard that runs the
    draw pile dry reshuffles through the same generator, so two differently
    played matches desynchronise, and mirroring or pairing two seats (the whole
    point of a paired tournament) becomes meaningless. The reference fixed this
    by forking one generator; this port just makes two of them, one named.

DESIGN DECISION — the reference's dead branch, defined here.
    The reference calls `self._end_lance_envite(matched=True)` when every
    opponent folds after an envite, and never defines that method: the path
    raises AttributeError, so a real bet chain that ends in a fold-out is a
    crash, not a rule. It cannot even fire through the public API — only the
    holder's side may `paso`, and an opponent always answers with
    quiero/no-quiero — but the state is one a fixture can build by hand, and
    there the reference dies. This port settles it the only way the surrounding
    code makes sense: the folders concede, so the holder's team collects the
    pending stake as a matched bet plus the jugada value. `_advance_envite_seat`
    has the same shaped guard (a raise whose next unfolded seat is the holder,
    which a raise can never produce because the raiser becomes the holder);
    both branches are unreachable through `legal_actions` and are kept because
    they are rules, not crashes, when a caller drives the state directly.

DESIGN DECISION — `strength` is a percentile, not a point sum.
    "How good is this hand" has to mean the same thing in every lance, or a
    threshold means four different things. A raw sum does not (tres and rey are
    both 10 points but different Grande cards), and for Chica it points the
    wrong way. `strength` ranks a hand among ALL 4-card hands the deck can deal
    at that lance, using the engine's own comparison, so a higher percentile is
    always a better hand — Chica included. It is the mid-rank percentile (ties
    count half), which makes the mean over random hands exactly 0.5 in every
    lance: one comparable scale. Ties therefore matter, and Pares is where they
    show: half of all hands hold no pares at all, so that whole class lands at
    its own mass/2 — 0.25, not the bottom — rather than being pinned at 0.0.
    Dropping ties instead would put over half of all hands at exactly 0.0 and
    the mean at 0.38, which is not a scale a tercile or a calibration curve can
    read.

DESIGN DECISION — what a mus discard payload is.
    `{"action": "discard", "cards": ["rey de oros", ...]}` names the cards to
    THROW AWAY (1 to 4), as the reference did. A name must resolve to exactly
    one card of the hand: the full "rey de oros", or a bare rank only when it
    names exactly one card. The reference matched loose substrings and took the
    first hit; refusing the ambiguity means a payload means one thing.

Dropped from the reference on purpose (this course does not grade them, and
each is machinery to maintain): the seña/bluff vocabulary, the partial
observability API (`reference_card.py`), the `os.environ` knobs (they are
constructor arguments here), the vaca callback, the JSONL writer, the
mus-ordago (an ordago here is a bet in the ENVITE phase, not a pre-mus one),
and `ENVITE_MAX`/`MUS_ROUNDS_MAX` are instance settings.
"""

import itertools
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, auto
from random import Random

# --------------------------------------------------------------------------
# The rules, as data
# --------------------------------------------------------------------------

PALOS = ("oros", "copas", "espadas", "bastos")
# Physical rank order, as, dos, ... rey. `Card.rank_index` is an index here.
RANKS = ("as", "dos", "tres", "cuatro", "cinco", "seis", "siete", "sota",
         "caballo", "rey")

TEAM_OF = {0: 0, 1: 1, 2: 0, 3: 1}

# Figures and tres count 10, as and dos count 1, the rest are their own number.
CARD_POINTS = {
    "as": 1, "dos": 1, "tres": 10, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "sota": 10, "caballo": 10, "rey": 10,
}

# Grande: tres = rey (12) on top, then caballo, sota, 7..4, and dos beats as.
# The same table is the equivalence classes for pares (only tres = rey).
RANK_GRANDE = {"tres": 12, "rey": 12, "caballo": 11, "sota": 10, "siete": 7,
               "seis": 6, "cinco": 5, "cuatro": 4, "dos": 2, "as": 1}

# Chica: the low cards are the good ones. Higher value = better card, so the
# engine compares the same way it does for Grande.
RANK_CHICA = {"as": 11, "dos": 10, "tres": 9, "rey": 9, "cuatro": 8,
              "cinco": 7, "seis": 6, "siete": 5, "sota": 2, "caballo": 1}

JUEGO_TOTALS = tuple(range(31, 41))
# 31 is strongest, then 32, then 40 down to 33.
JUEGO_RANK = {31: 10, 32: 9, 40: 8, 39: 7, 38: 6, 37: 5, 36: 4, 35: 3,
              34: 2, 33: 1}

VACA_TARGET = 40
LANCE_NAMES = ("Grande", "Chica", "Pares", "Juego")
# Pares and Juego open with a truthful tengo/no-tengo round; Grande and Chica
# go straight to the named bets.
DECLARATION_LANCES = (2, 3)

# A hand may not run forever. The reference has no such rail and can only be
# stopped by its policy; here a hand that applies this many actions refuses the
# next one with `TurnLimitExceeded` instead of hanging. Comfortably above the
# longest legal hand at the default settings (`envite_max=40`, `mus_rounds=2`);
# lower it on a Table (`table.turn_limit = 20`) to test the rail itself.
TURN_LIMIT = 512


def team_of(seat: int) -> int:
    """The team that owns `seat`: 0 for seats 0 and 2, 1 for seats 1 and 3."""
    try:
        return TEAM_OF[seat]
    except (KeyError, TypeError):
        raise IllegalAction(f"no such seat: {seat!r}") from None


# --------------------------------------------------------------------------
# The deck
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Card:
    """One of the forty. `str(card)` is how a discard payload names it."""

    rank: str
    palo: str

    @property
    def rank_index(self) -> int:
        """Index in physical rank order, so rey is the highest and as lowest."""
        return RANKS.index(self.rank)

    def __str__(self) -> str:
        return f"{self.rank} de {self.palo}"


def make_deck() -> list[Card]:
    """A fresh forty-card Spanish deck, one card per (rank, palo)."""
    return [Card(rank, palo) for palo in PALOS for rank in RANKS]


@dataclass
class _EnviteState:
    """The state of one named-bet chain. Read it through `Table.envite`."""

    stake: int = 0                    # the unmatched amount on the table
    previous: int = 0                 # what declining costs the seat asked
    holder: int | None = None         # the seat that last bet or raised
    folded: set[int] = field(default_factory=set)   # seats out of THIS chain
    spoke: set[int] = field(default_factory=set)    # seats that spoke at 0


# --------------------------------------------------------------------------
# Refusals and phases
# --------------------------------------------------------------------------


class IllegalAction(Exception):
    """The engine refused: wrong seat, unknown action name, or a payload the
    rules forbid. `apply` validates before it mutates, so a refused action
    leaves the table byte-identical."""


class TurnLimitExceeded(Exception):
    """A hand ran past `Table.turn_limit` accepted actions.

    Deliberately NOT an `IllegalAction`: a seat that answers badly is data for
    the harness to count, but a hand that never ends is a broken driver, and a
    program that treats it as a rejection hides a hang behind a behaviour
    metric. Let it propagate.
    """


class Phase(Enum):
    MUS_REQUEST = auto()      # "mus?" around the table; a 'no' skips the draws
    MUS_DRAW = auto()         # a seat that asked for mus discards 1-4 cards
    DECLARE = auto()          # truthful tengo/no-tengo (Pares and Juego)
    ENVITE = auto()           # named bets on the lance being played
    ORDAGO_RESPONSE = auto()  # the seat after an ordago says quiero/no-quiero
    DONE = auto()


# --------------------------------------------------------------------------
# The comparable values — one per lance, tuples that sort the right way
# --------------------------------------------------------------------------
#
# These are module functions, not methods, because `strength` needs them for
# hands that are not on a table (it ranks a hand against every hand the deck
# can deal). `Table._lance_value` and friends are thin aliases.


def _hand_points(cards) -> int:
    return sum(CARD_POINTS[card.rank] for card in cards)


def _grande_value(cards) -> tuple[int, ...]:
    """Descending RANK_GRANDE of the cards: bigger tuple = better hand."""
    return tuple(sorted((RANK_GRANDE[card.rank] for card in cards), reverse=True))


def _chica_value(cards) -> tuple[int, ...]:
    """Descending RANK_CHICA of the cards: bigger tuple = better hand."""
    return tuple(sorted((RANK_CHICA[card.rank] for card in cards), reverse=True))


def _pares_value(cards) -> tuple[int, tuple[int, ...]]:
    """(category, ranks): duples 3 > medias 2 > par 1 > nothing 0.

    Four of a kind is a duples of its own mus-rank (rey+tres+rey+tres is a
    duples of reyes). as and dos are different ranks, so as+dos is not a pair,
    while dos+dos+as+as is a duples.
    """
    counts = Counter(RANK_GRANDE[card.rank] for card in cards)
    four = [r for r, n in counts.items() if n >= 4]
    if four:
        return (3, (four[0], four[0]))
    paired = sorted((r for r, n in counts.items() if n >= 2), reverse=True)
    if len(paired) >= 2:
        return (3, tuple(paired))
    if paired:
        rank = paired[0]
        return (2, (rank,)) if counts[rank] >= 3 else (1, (rank,))
    return (0, ())


def _juego_value(cards) -> tuple[int, int]:
    """(has_juego, strength): 1 for 31-40 (31 strongest), 0 with the point
    total otherwise — a punto loses to any juego, and among puntos more is
    better."""
    total = _hand_points(cards)
    if total in JUEGO_RANK:
        return (1, JUEGO_RANK[total])
    return (0, total)


def _lance_value(name: str, cards):
    """The comparable value of `cards` at lance `name`. All values sort so that
    bigger is better; that is the whole comparison."""
    if name == "Grande":
        return _grande_value(cards)
    if name == "Chica":
        return _chica_value(cards)
    if name == "Pares":
        return _pares_value(cards)
    if name == "Juego":
        return _juego_value(cards)
    if name == "punto":
        # The punto block is played by totals <= 30, so the value is the raw
        # total and nothing else: a hand holding a juego is not in the block.
        return _hand_points(cards)
    raise ValueError(f"no such lance: {name!r}")


_DECK = tuple(make_deck())

# The largest point total that is NOT a juego: the punto block is 4..30, and a
# hand of 31-40 is not eligible for it (it would take the lance outright).
PUNTO_MAX = min(JUEGO_TOTALS) - 1

# Write-once cache: for each lance, the sorted values of all C(40, 4) = 91,390
# hands the deck can deal. A pure function of the rules, so it is not state: no
# Table can influence another through it, and it is only ever filled.
_VALUE_TABLES: dict[str, tuple] = {}


def _value_table(lance: str) -> tuple:
    """Every value the lance can take, sorted. Built once, on first use.

    The four named lances rank every four-card hand. "punto" ranks only the
    hands that can play a punto (total <= 30), so a hand holding a juego is
    above all of them and its percentile there is 1.0.
    """
    table = _VALUE_TABLES.get(lance)
    if table is None:
        values = [_lance_value(lance, list(combo))
                  for combo in itertools.combinations(_DECK, 4)]
        if lance == "punto":
            values = [value for value in values if value <= PUNTO_MAX]
        table = tuple(sorted(values))
        _VALUE_TABLES[lance] = table
    return table


# --------------------------------------------------------------------------
# The table
# --------------------------------------------------------------------------


class Table:
    """One mus table: four seats, two teams, one hand at a time.

    State a caller may read (all plain attributes unless noted):

        hand_index    the 0-based number of the hand in this match (-1 before
                      the first `deal()`); the mano rotates with it
        mano          the seat that speaks first this hand
        current_seat  the seat whose turn it is
        hands         {seat: [Card, Card, Card, Card]}
        draw_pile     the undealt remainder (24 cards at the deal)
        discard_pile  cards thrown away, recycled into the draw pile
        phase         the `Phase` being played
        turns         accepted actions in the CURRENT hand
        mus_want      the seats that asked for mus in the current request round
        mus_draws     how many discard rounds this hand has used
        lance_index   0..3 while a lance is played, 4 once the hand is over
        declared      {seat: bool} of the current tengo/no-tengo round
        points_a/b    piedras on the table now (reset by a vaca)
        vacas_a/b     vacas won in the match
        hand_gain_a/b piedras each team won in the CURRENT hand (a vaca does
                      NOT reset these)
        hand_winner   0, 1 or None once the hand is DONE
        jugadas       [(lance, winning team or None)] resolved so far
        lance         property: "grande"/"chica"/"pares"/"juego"/"punto", or
                      None while the mus phase runs or the hand is DONE
        envite        property: a fresh dict describing the bet on the table

    Two settings move the rules without changing them:

        mus_rounds   how many request+discard rounds a hand may have (default 2)
        envite_max   the stake at which no more raising is legal (default 40);
                     a reenvido from just below it still doubles past it, as in
                     the reference
        turn_limit   accepted actions in one hand before the engine refuses
    """

    def __init__(self, *, seed: int, deal_seed: int | None = None,
                 mus_rounds: int = 2, envite_max: int = 40):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an int")
        if deal_seed is not None and (isinstance(deal_seed, bool)
                                      or not isinstance(deal_seed, int)):
            raise TypeError("deal_seed must be an int or None")
        if isinstance(mus_rounds, bool) or not isinstance(mus_rounds, int) \
                or mus_rounds < 1:
            raise ValueError("mus_rounds must be an int >= 1")
        if isinstance(envite_max, bool) or not isinstance(envite_max, int) \
                or envite_max < 2:
            raise ValueError("envite_max must be an int >= 2")

        self.seed = seed
        self.deal_seed = seed if deal_seed is None else deal_seed
        self.mus_rounds = mus_rounds
        self.envite_max = envite_max
        self.turn_limit = TURN_LIMIT

        # The deal stream: advanced by deal(), never by play.
        self.deal_rng = Random(self.deal_seed)
        # The play stream: the reshuffles a discard causes. A different object
        # even when it was seeded from the same number.
        self.rng = Random(seed)

        self.hand_index = -1
        self.mano = 0
        self.current_seat = 0
        self.hands: dict[int, list[Card]] = {}
        self.draw_pile: list[Card] = []
        self.discard_pile: list[Card] = []
        self.phase = Phase.MUS_REQUEST
        self.turns = 0
        self.mus_want: set[int] = set()
        self.mus_draws = 0
        self.lance_index = 0
        self.declared: dict[int, bool] = {}
        self._envite = _EnviteState()
        self.points_a = 0
        self.points_b = 0
        self.vacas_a = 0
        self.vacas_b = 0
        self.hand_gain_a = 0
        self.hand_gain_b = 0
        self.hand_winner: int | None = None
        self.jugadas: list[tuple[str, int | None]] = []
        self.locked_envites: list[tuple[str, int, int]] = []
        self._ordago_caller: int | None = None

    def __repr__(self) -> str:
        return (f"Table(hand_index={self.hand_index}, phase={self.phase.name}, "
                f"seat={self.current_seat}, points={self.points_a}/"
                f"{self.points_b}, vacas={self.vacas_a}/{self.vacas_b})")

    # ---------------- state a policy reads ----------------

    @property
    def lance(self) -> str | None:
        """The lance under way, lower case.

        "punto" is the Juego lance played by hands where nobody holds a juego:
        the point total decides it, and 31-40 does not win it. None while the
        mus phase runs, or once the hand is DONE (and once the last lance has
        been played, whatever the phase a caller left the table in).
        """
        if not self.hands or not 0 <= self.lance_index < len(LANCE_NAMES):
            return None
        if self.phase in (Phase.MUS_REQUEST, Phase.MUS_DRAW, Phase.DONE):
            return None
        name = LANCE_NAMES[self.lance_index]
        if name == "Juego" and not any(
                _hand_points(self.hands[seat]) in JUEGO_TOTALS for seat in self.hands):
            return "punto"
        return name.lower()

    @property
    def envite(self) -> dict:
        """A fresh dict describing the bet on the table, never the internal
        object (mutate the copy freely):

            stake        the amount on the table now (0 when nobody bet)
            previous     what declining costs the seat being asked (0 when the
                         holder has not been called; the 1-'deje' floor applies
                         when a decline is COLLECTED, not here)
            holder       the seat that last bet or raised, None when nobody has
            holder_team  team_of(holder), or None
            facing       {seat: bool}: the opposing-team seats that still owe
                         this bet an answer (a seat whose PARTNER bet is not
                         facing anything, and a folded seat is out)
        """
        holder = self._envite.holder
        holder_team = None if holder is None else TEAM_OF[holder]
        pending = self._envite.stake > 0 and holder_team is not None
        facing = {
            seat: bool(pending and TEAM_OF[seat] != holder_team
                       and seat not in self._envite.folded)
            for seat in range(4)
        }
        return {
            "stake": self._envite.stake,
            "previous": self._envite.previous,
            "holder": holder,
            "holder_team": holder_team,
            "facing": facing,
        }

    # ---------------- dealing ----------------

    def deal(self) -> dict[int, list[Card]]:
        """Shuffle from the deal stream and deal the next hand.

        The mano rotates with the hand number. Points and vacas carry over;
        everything scoped to a hand is reset. Calling it mid-hand abandons that
        hand — the deal stream advances either way, and only the seed decides
        the cards.
        """
        self.hand_index += 1
        self.mano = self.hand_index % 4
        self.current_seat = self.mano
        self.phase = Phase.MUS_REQUEST
        self.turns = 0
        self.mus_want = set()
        self.mus_draws = 0
        self.lance_index = 0
        self.declared = {}
        self._envite = _EnviteState()
        self.hand_gain_a = 0
        self.hand_gain_b = 0
        self.hand_winner = None
        self.jugadas = []
        self.locked_envites = []
        self._ordago_caller = None

        deck = make_deck()
        self.deal_rng.shuffle(deck)
        self.hands = {seat: deck[seat * 4:(seat + 1) * 4] for seat in range(4)}
        self.draw_pile = deck[16:]
        self.discard_pile = []
        return self.hands

    # ---------------- the comparable values ----------------

    @staticmethod
    def hand_points(cards) -> int:
        """The mus point total of `cards` (the Juego/Punto total)."""
        return _hand_points(cards)

    def _grande_value(self, cards):
        return _grande_value(cards)

    def _chica_value(self, cards):
        return _chica_value(cards)

    def _pares_value(self, cards):
        return _pares_value(cards)

    def _juego_value(self, cards):
        return _juego_value(cards)

    def _lance_value(self, name: str, cards):
        return _lance_value(name, cards)

    def _team_best(self, team: int, name: str):
        """The better of the team's two hands at `name` — a team plays its best
        four cards, as the reference rules it."""
        return max((self.hands[seat] for seat in range(4) if TEAM_OF[seat] == team),
                   key=lambda cards: _lance_value(name, cards))

    def _lance_winner(self, name: str) -> int | None:
        """The team that takes `name` with the hands as dealt, None on a tie."""
        if not self.hands:
            raise IllegalAction("no hand in progress; call deal() first")
        mine = _lance_value(name, self._team_best(0, name))
        theirs = _lance_value(name, self._team_best(1, name))
        if mine > theirs:
            return 0
        if theirs > mine:
            return 1
        return None

    def _punto_winner(self) -> int | None:
        """The team that takes the punto block with the hands as dealt.

        The punto is played by point totals <= 30; a hand holding a juego is not
        eligible (it would take the Juego lance outright), so a team whose two
        hands both hold one has no punto to play and loses this comparison. In
        play that case cannot arise: `Table.lance` calls a lance "punto" only
        when nobody holds a juego.
        """
        if not self.hands:
            raise IllegalAction("no hand in progress; call deal() first")
        best = {}
        for team in (0, 1):
            totals = [_hand_points(self.hands[seat]) for seat in range(4)
                      if TEAM_OF[seat] == team]
            eligible = [total for total in totals if total <= PUNTO_MAX]
            best[team] = max(eligible) if eligible else None
        if best[0] == best[1]:
            return None
        if best[0] is None:
            return 1
        if best[1] is None:
            return 0
        return 0 if best[0] > best[1] else 1

    def compare_jugadas(self) -> list[tuple[str, int | None]]:
        """The four lances in order, each with the team that takes it right now
        (None on a tie), from the hands as dealt."""
        if not self.hands:
            raise IllegalAction("no hand in progress; call deal() first")
        return [(name, self._lance_winner(name)) for name in LANCE_NAMES]

    def declaration_of(self, seat: int) -> str:
        """The only tengo/no-tengo `seat` may declare at the DECLARE lance that
        is running — the truth, read from its own hand. The engine rejects the
        other answer, so a policy that asks the engine never lies."""
        if self.lance_index not in DECLARATION_LANCES:
            raise IllegalAction(f"no declaration is being taken (lance_index="
                                f"{self.lance_index})")
        if seat not in self.hands:
            raise IllegalAction(f"no such seat: {seat!r}")
        hand = self.hands[seat]
        if LANCE_NAMES[self.lance_index] == "Pares":
            has = _pares_value(hand)[0] > 0
        else:
            has = _hand_points(hand) in JUEGO_TOTALS
        return "tengo" if has else "no-tengo"

    # ---------------- legal actions ----------------

    def legal_actions(self, seat: int) -> list[str]:
        """The action names `seat` may play now.

        [] whenever it is not this seat's turn, which includes every seat
        before the first `deal()` and after the hand is DONE.
        """
        if not self.hands or seat != self.current_seat:
            return []
        if self.phase == Phase.MUS_REQUEST:
            return ["mus", "no"]
        if self.phase == Phase.MUS_DRAW:
            return ["discard"] if seat in self.mus_want else []
        if self.phase == Phase.DECLARE:
            return ["tengo", "no-tengo"]
        if self.phase == Phase.ENVITE:
            return self._envite_legal(seat)
        if self.phase == Phase.ORDAGO_RESPONSE:
            return ["quiero", "no-quiero"]
        return []

    def _envite_legal(self, seat: int) -> list[str]:
        envite = self._envite
        if seat in envite.folded:
            return []
        if envite.stake == 0:
            return ["paso", "envido", "ordago"]
        can_raise = envite.stake < self.envite_max
        mine = envite.holder is not None and TEAM_OF[seat] == TEAM_OF[envite.holder]
        if mine:
            # Our own bet: we may pass (and be out of the chain) or raise it.
            actions = ["paso"]
            if can_raise:
                actions.append("y-yo")
                if envite.stake >= 4:
                    actions.append("reenvido")
        else:
            # Their bet: answer it.
            actions = ["quiero", "no-quiero"]
            if can_raise:
                actions.append("y-yo")
                if envite.stake >= 4:
                    actions.append("reenvido")
        actions.append("ordago")
        return actions

    # ---------------- apply ----------------

    def apply(self, seat: int, action: dict) -> None:
        """Play `action` for `seat`.

        Atomic: the turn, the seat, the action name and the payload are all
        checked first, so a refused action raises `IllegalAction` and changes
        nothing. Raising `TurnLimitExceeded` (the hand is looping) likewise
        changes nothing.
        """
        if self.turns >= self.turn_limit:
            raise TurnLimitExceeded(
                f"hand {self.hand_index} already applied {self.turns} actions")
        if seat not in TEAM_OF:
            raise IllegalAction(f"no such seat: {seat!r}")
        if not isinstance(action, dict):
            raise IllegalAction("an action is a dict, e.g. {'action': 'mus'}")
        if not self.hands:
            raise IllegalAction("no hand in progress; call deal() first")
        if seat != self.current_seat:
            raise IllegalAction(
                f"not seat {seat}'s turn (current={self.current_seat})")
        name = action.get("action")
        legal = self.legal_actions(seat)
        if name not in legal:
            raise IllegalAction(
                f"illegal action {name!r} in phase {self.phase.name} "
                f"(legal: {legal})")

        # Resolve the payload now, while nothing has changed.
        discard: list[Card] = []
        if name == "discard":
            discard = self._resolve_discard(seat, action.get("cards"))
        elif self.phase == Phase.DECLARE:
            truthful = self.declaration_of(seat)
            if name != truthful:
                raise IllegalAction(
                    f"false declaration for "
                    f"{LANCE_NAMES[self.lance_index].lower()}: the only legal "
                    f"action is {truthful!r}")

        # Past this line nothing raises: the action lands whole.
        self.turns += 1
        if self.phase == Phase.MUS_REQUEST:
            self._apply_mus_request(seat, name)
        elif self.phase == Phase.MUS_DRAW:
            self._apply_draw(seat, discard)
        elif self.phase == Phase.DECLARE:
            self._apply_declare(seat, name)
        elif self.phase == Phase.ENVITE:
            self._apply_envite(seat, name)
        else:
            self._apply_ordago_response(seat, name)

    # ---------------- mus ----------------

    def _apply_mus_request(self, seat: int, name: str) -> None:
        if name == "no":
            # "No hay mus": nobody discards, the lances start now.
            self._start_lances()
            return
        self.mus_want.add(seat)
        after = (seat + 1) % 4
        if after == self.mano:
            self._start_draw()
        else:
            self.current_seat = after

    def _start_draw(self) -> None:
        self.mus_draws += 1
        self.phase = Phase.MUS_DRAW
        self.current_seat = self._next_wanting()

    def _next_wanting(self) -> int:
        """The next seat that asked for mus, in turn order from the mano."""
        return min(self.mus_want, key=lambda seat: (seat - self.mano) % 4)

    def _apply_draw(self, seat: int, discard: list[Card]) -> None:
        self._redraw(seat, discard)
        self.mus_want.discard(seat)
        if self.mus_want:
            self.current_seat = self._next_wanting()
        elif self.mus_draws < self.mus_rounds:
            # Discards may repeat: open another request round.
            self.phase = Phase.MUS_REQUEST
            self.mus_want = set()
            self.current_seat = self.mano
        else:
            self._start_lances()

    def _redraw(self, seat: int, discard: list[Card]) -> None:
        """Throw `discard` away and draw as many back.

        Only draw pile and discards move; the deck is conserved. An empty draw
        pile is refilled from the discards through the PLAY stream — this is the
        reshuffle that must never touch the deal stream.
        """
        for card in discard:
            self.hands[seat].remove(card)
            self.discard_pile.append(card)
            if not self.draw_pile:
                self.rng.shuffle(self.discard_pile)
                self.draw_pile = self.discard_pile
                self.discard_pile = []
            self.hands[seat].append(self.draw_pile.pop())

    def _resolve_discard(self, seat: int, names) -> list[Card]:
        """The cards `names` asks to throw away, or a refusal.

        Raises before anything is touched. A name is the full `str(card)` of a
        card in the hand, or a bare rank that names exactly one of them.
        """
        if not isinstance(names, list):
            raise IllegalAction("discard requires a 'cards' list")
        if not 1 <= len(names) <= 4:
            raise IllegalAction("must discard between 1 and 4 cards")
        hand = self.hands[seat]
        chosen: list[Card] = []
        for name in names:
            if not isinstance(name, str) or not name.strip():
                raise IllegalAction("discard card names must be nonempty strings")
            wanted = name.strip().lower()
            matches = [card for card in hand
                       if card not in chosen
                       and (wanted == str(card) or wanted == card.rank)]
            if not matches:
                raise IllegalAction(f"discard card not available: {name!r}")
            if len(matches) > 1:
                raise IllegalAction(
                    f"ambiguous discard card {name!r}: matches "
                    f"{sorted(str(card) for card in matches)}")
            chosen.append(matches[0])
        return chosen

    # ---------------- the lances ----------------

    def _start_lances(self) -> None:
        self.lance_index = 0
        self._begin_lance()

    def _begin_lance(self) -> None:
        """Route the lance: Pares and Juego take declarations first."""
        self.declared = {}
        self.current_seat = self.mano
        self.phase = (Phase.DECLARE if self.lance_index in DECLARATION_LANCES
                      else Phase.ENVITE)

    def _apply_declare(self, seat: int, name: str) -> None:
        lance = LANCE_NAMES[self.lance_index]
        truthful = self.declaration_of(seat)
        if name != truthful:
            raise IllegalAction(
                f"false declaration for {lance.lower()}: the only legal action "
                f"is {truthful!r}")
        self.declared[seat] = (name == "tengo")
        if len(self.declared) == 4:
            self._resolve_declarations()
        else:
            self.current_seat = (seat + 1) % 4

    def _resolve_declarations(self) -> None:
        """Both teams in: play the lance. One team: it takes the lance. Neither:
        Pares is nothing to play, Juego is the punto's named bets."""
        lance = LANCE_NAMES[self.lance_index]
        team_a = self.declared[0] or self.declared[2]
        team_b = self.declared[1] or self.declared[3]
        if team_a and team_b:
            self._envite = _EnviteState()
            self.phase = Phase.ENVITE
            self.current_seat = self.mano
        elif team_a or team_b:
            winner = 0 if team_a else 1
            self._award_lance(lance, winner)
            self.jugadas.append((lance, winner))
            self._advance_lance()
        elif lance == "Pares":
            self.jugadas.append((lance, None))
            self._advance_lance()
        else:
            # Nobody has juego: the punto is what the named bets are about.
            self._envite = _EnviteState()
            self.phase = Phase.ENVITE
            self.current_seat = self.mano

    def _advance_lance(self) -> None:
        self.lance_index += 1
        if self.lance_index >= len(LANCE_NAMES):
            self._settle_locked_envites()
            self._apply_vaca()
            self.phase = Phase.DONE
            self._set_hand_winner()
        else:
            self._envite = _EnviteState()
            self._begin_lance()

    def _award_lance(self, name: str, winner: int) -> None:
        if name in ("Grande", "Chica"):
            self._add_points(winner, 1)
        elif name == "Pares":
            self._award_pares(winner)
        else:
            self._award_juego(winner)

    def _award_pares(self, winner: int) -> None:
        """Each of the winning team's hands pays its own category (the
        reference's rule; a team can be paid twice)."""
        for seat in range(4):
            if TEAM_OF[seat] == winner:
                category = _pares_value(self.hands[seat])[0]
                if category:
                    self._add_points(winner, category)

    def _award_juego(self, winner: int) -> None:
        """31 pays 3, any other juego pays 2; with no juego on the team the
        punto pays 1. Again per hand, as the reference rules it."""
        seats = [seat for seat in range(4) if TEAM_OF[seat] == winner]
        if any(_hand_points(self.hands[seat]) in JUEGO_TOTALS for seat in seats):
            for seat in seats:
                total = _hand_points(self.hands[seat])
                if total in JUEGO_TOTALS:
                    self._add_points(winner, 3 if total == 31 else 2)
        else:
            self._add_points(winner, 1)          # the punto

    # ---------------- the named bets ----------------

    def _apply_envite(self, seat: int, name: str) -> None:
        envite = self._envite
        if name == "paso":
            if envite.stake == 0:
                envite.spoke.add(seat)
                after = self._next_unfolded(seat)
                if len(envite.spoke) == 4:
                    self._end_lance_pass()
                else:
                    self.current_seat = after
                return
            envite.folded.add(seat)
            after = self._next_unfolded(seat)
            unfolded = [s for s in range(4) if s not in envite.folded]
            if after == envite.holder and all(
                    TEAM_OF[s] == TEAM_OF[envite.holder] for s in unfolded):
                self._end_lance_envite()
            else:
                self.current_seat = after
        elif name == "envido":
            envite.previous, envite.stake, envite.holder = 0, 2, seat
            envite.spoke = set()
            self._advance_envite_seat(seat)
        elif name == "y-yo":
            envite.previous, envite.stake = envite.stake, envite.stake + 2
            envite.holder = seat
            envite.spoke = set()
            self._advance_envite_seat(seat)
        elif name == "reenvido":
            envite.previous, envite.stake = envite.stake, envite.stake * 2
            envite.holder = seat
            envite.spoke = set()
            self._advance_envite_seat(seat)
        elif name == "quiero":
            # Accepted: the stake is collected at the showdown.
            self.locked_envites.append(
                (LANCE_NAMES[self.lance_index], envite.stake, envite.holder))
            self.jugadas.append((LANCE_NAMES[self.lance_index], None))
            self._advance_lance()
        elif name == "no-quiero":
            self._settle_decline()
        else:                                    # "ordago"
            self._ordago_caller = seat
            self.phase = Phase.ORDAGO_RESPONSE
            self.current_seat = (seat + 1) % 4

    def _next_unfolded(self, seat: int) -> int:
        after = (seat + 1) % 4
        for _ in range(4):
            if after not in self._envite.folded:
                return after
            after = (after + 1) % 4
        return after

    def _advance_envite_seat(self, seat: int) -> None:
        # `seat` is the seat that just raised, so the next unfolded seat can
        # never be the holder: the guard below is unreachable through legal
        # play (see the module docstring) and settles a hand-built state.
        envite = self._envite
        after = self._next_unfolded(seat)
        if after == envite.holder and envite.stake > 0:
            # Nobody accepted or declined: the bet stands, to be compared when
            # the cards are shown.
            self.locked_envites.append(
                (LANCE_NAMES[self.lance_index], envite.stake, envite.holder))
            self.jugadas.append((LANCE_NAMES[self.lance_index], None))
            self._advance_lance()
        else:
            self.current_seat = after

    def _end_lance_pass(self) -> None:
        """Everybody passed at stake 0: the better four cards take the lance."""
        name = LANCE_NAMES[self.lance_index]
        winner = self._lance_winner(name)
        if winner is not None:
            self._award_lance(name, winner)
        self.jugadas.append((name, winner))
        self._advance_lance()

    def _end_lance_envite(self) -> None:
        """Every opponent folded after an envite: the holder's team collects
        the pending stake as a matched bet plus the jugada value.

        This is the branch the reference calls and never defines — see the
        module docstring; here it is a rule instead of an AttributeError. No
        legal play reaches it (an opponent answers an envite with
        quiero/no-quiero, never paso); it settles the state a caller builds by
        hand.
        """
        name = LANCE_NAMES[self.lance_index]
        holder_team = TEAM_OF[self._envite.holder]
        self._add_points(holder_team, self._envite.stake)
        self._award_lance(name, holder_team)
        self.jugadas.append((name, holder_team))
        self._advance_lance()

    def _settle_decline(self) -> None:
        """no-quiero: the holder's team is paid the previous stake (or the
        1-'deje' floor) and takes the jugada without a comparison."""
        name = LANCE_NAMES[self.lance_index]
        holder_team = TEAM_OF[self._envite.holder]
        stake = self._envite.previous if self._envite.previous > 0 else 1
        self._add_points(holder_team, stake)
        self._award_lance(name, holder_team)
        self.jugadas.append((name, holder_team))
        self._advance_lance()

    def _settle_locked_envites(self) -> None:
        """Showdown: the cards are shown, so every locked bet is collected by
        whoever wins that lance."""
        for name, stake, _holder in self.locked_envites:
            winner = self._lance_winner(name)
            if winner is not None:
                self._add_points(winner, stake)
                self._award_lance(name, winner)
            for index, (recorded, team) in enumerate(self.jugadas):
                if recorded == name and team is None:
                    self.jugadas[index] = (name, winner)
                    break

    # ---------------- ordago ----------------

    def _apply_ordago_response(self, seat: int, name: str) -> None:
        if name == "quiero":
            self._resolve_ordago()
        else:
            self._resolve_ordago_declined()
        self._ordago_caller = None

    def _resolve_ordago(self) -> None:
        """Ordago accepted: the whole game (40 piedras) rides on the jugadas."""
        self._settle_locked_envites()
        self.jugadas = self.compare_jugadas()
        won_a = sum(1 for _, team in self.jugadas if team == 0)
        won_b = sum(1 for _, team in self.jugadas if team == 1)
        if won_a != won_b:
            self._add_points(0 if won_a > won_b else 1, VACA_TARGET)
        else:
            grande = self._lance_winner("Grande")
            if grande is None:
                self._add_points(0, VACA_TARGET // 2)
                self._add_points(1, VACA_TARGET // 2)
            else:
                self._add_points(grande, VACA_TARGET)
        self._apply_vaca()
        self.phase = Phase.DONE
        self._set_hand_winner()

    def _resolve_ordago_declined(self) -> None:
        """Ordago declined: the caller's team takes the stake and the jugada."""
        caller = self._ordago_caller
        name = LANCE_NAMES[self.lance_index]
        stake = self._envite.previous if self._envite.previous > 0 else 1
        self._add_points(TEAM_OF[caller], stake)
        self._award_lance(name, TEAM_OF[caller])
        self.jugadas.append((name, TEAM_OF[caller]))
        self._advance_lance()

    # ---------------- scoring ----------------

    def _add_points(self, team: int, amount: int) -> None:
        if team == 0:
            self.points_a += amount
            self.hand_gain_a += amount
        else:
            self.points_b += amount
            self.hand_gain_b += amount

    def _apply_vaca(self) -> None:
        """Every 40 piedras is a vaca; a vaca puts BOTH counters back to 0.

        The per-hand gains are not counters: they are what the hand won, and
        they survive the reset.
        """
        vacas_a = self.points_a // VACA_TARGET
        vacas_b = self.points_b // VACA_TARGET
        self.vacas_a += vacas_a
        self.vacas_b += vacas_b
        if vacas_a or vacas_b:
            self.points_a = 0
            self.points_b = 0

    def _set_hand_winner(self) -> None:
        if self.hand_gain_a > self.hand_gain_b:
            self.hand_winner = 0
        elif self.hand_gain_b > self.hand_gain_a:
            self.hand_winner = 1
        else:
            self.hand_winner = None

    # ---------------- table-scoped oracles ----------------

    def strength(self, seat: int, lance: str | None = None) -> float | None:
        """This table's `strength(table, seat, lance)`."""
        return strength(self, seat, lance)

    def would_win(self, seat: int, lance: str | None = None) -> bool | None:
        """This table's `would_win(table, seat, lance)`."""
        return would_win(self, seat, lance)

    def lance_winner(self, lance: str | None = None) -> int | None:
        """This table's `lance_winner(table, lance)`."""
        return lance_winner(self, lance)

    def default_action(self, seat: int) -> dict | None:
        """This table's `default_action(table, seat)`."""
        return default_action(self, seat)


# --------------------------------------------------------------------------
# The oracles: how strong is a hand, and who wins a lance
# --------------------------------------------------------------------------


def _resolve_lance(name) -> str | None:
    """Canonical key for a lance name: a LANCE_NAMES entry, or "punto"."""
    text = str(name).strip().lower()
    if text == "punto":
        return "punto"
    for known in LANCE_NAMES:
        if known.lower() == text:
            return known
    return None


def _lance_of(table: Table, lance: str | None) -> str | None:
    """The lance a query is about.

    None asks for the lance the table is playing right now, resolved through
    `Table.lance` — which is None while the mus phase runs and once the hand is
    DONE, so there is nothing to answer there. A name is matched case
    insensitively; unknown names resolve to None.
    """
    if lance is None:
        current = table.lance
        return None if current is None else _resolve_lance(current)
    if not isinstance(lance, str):
        return None
    return _resolve_lance(lance)


def strength(table: Table, seat: int, lance: str | None = None) -> float | None:
    """The seat's hand at `lance`, as a percentile in [0, 1].

    The rank is against EVERY four-card hand the deck can deal at that lance
    (91,390 of them, tabulated once per lance), measured with the engine's own
    comparison (`_lance_value`), so a higher percentile always means a better
    hand — for every lance, Chica included.

    The percentile is the mid-rank one: the fraction of hands this one beats,
    plus half of the hands it ties, over all of them. Two consequences matter
    downstream, and they are why this definition and not "beats / (beats +
    loses)":

      * the mean over random hands is exactly 0.5 in EVERY lance, so the four
        scales are comparable and a threshold means the same thing in all of
        them (a raw sum or a per-lance score is not comparable that way);
      * ties sit in the middle instead of being dropped. Pares is the extreme
        case: half of all hands hold no pares at all, so they are one tied
        class and they land at 0.25 together — half of their own mass — rather
        than all being pinned at 0.0, which is what "below average at Pares,
        not the worst possible hand" should say. The best hand lands at
        1 - (its own tie mass)/2 and the worst at (its tie mass)/2: as close
        to 1.0/0.0 as ties allow, and within 1/(2 * 91390) of them when the
        value is unique.

    "punto" is the Juego lance played by point totals <= 30: the percentile is
    against the hands that can play a punto, so a hand holding a juego — which
    would take the Juego lance outright — sits at the top of that scale.

    None when there is no hand or no lance to rank against: a seat outside
    0..3, an unknown lance name, or a table with no lance under way (in the mus
    phase, or once the hand is DONE — pass a lance explicitly to rank a hand
    after DONE).
    """
    name = _lance_of(table, lance)
    if name is None or seat not in table.hands:
        return None
    values = _value_table(name)
    value = _lance_value(name, table.hands[seat])
    below = bisect_left(values, value)
    at_or_below = bisect_right(values, value)
    return (below + at_or_below) / (2.0 * len(values))


def lance_winner(table: Table, lance: str | None = None) -> int | None:
    """The team that takes `lance` with the hands as dealt (None on a tie).

    "punto" is the punto block: the totals <= 30 decide it, higher is better,
    and hands holding a juego are not in it.

    None as well when there is nothing to score: no hand dealt, no lance under
    way, or an unknown lance name. This is the oracle a scorecard compares a
    seat's claims to.
    """
    name = _lance_of(table, lance)
    if name is None:
        return None
    if name == "punto":
        return table._punto_winner()
    return table._lance_winner(name)


def would_win(table: Table, seat: int, lance: str | None = None) -> bool | None:
    """Whether `seat`'s team takes `lance` with the hands as dealt.

    True when the team takes it outright, False when the other team does, None
    on a tie — and None when there is nothing to score (no hand dealt, unknown
    lance, or a seat outside 0..3).
    """
    winner = lance_winner(table, lance)
    if winner is None:
        return None
    team = TEAM_OF.get(seat)
    if team is None:
        return None
    return winner == team


def _keep_rule(hand) -> tuple[list[Card], list[Card]]:
    """Split a hand the way this engine keeps cards: mus-rank pairs first, then
    cards that can still pay for Grande/Chica (RANK_GRANDE >= 7). At most three
    cards are kept, so there is always at least one to throw away."""
    counts = Counter(RANK_GRANDE[card.rank] for card in hand)
    keep = [card for card in hand
            if counts[RANK_GRANDE[card.rank]] >= 2 or RANK_GRANDE[card.rank] >= 7]
    keep.sort(key=lambda card: (counts[RANK_GRANDE[card.rank]] >= 2,
                                RANK_GRANDE[card.rank], str(card)), reverse=True)
    keep = keep[:3]
    toss = [card for card in hand if card not in keep]
    return keep, toss


def _toss(hand, rng: Random | None = None) -> list[Card]:
    """The cards to throw away out of `hand`.

    Deterministic without `rng`; with one, the hand is shuffled first so the
    seed decides which of several equally keepable cards goes, instead of the
    order the cards happened to be dealt in.
    """
    ordered = list(hand)
    if rng is not None:
        rng.shuffle(ordered)
    _, toss = _keep_rule(ordered)
    return toss


def default_action(table: Table, seat: int) -> dict | None:
    """The engine's own legal action for `seat` right now, payload included.

    The fallback a harness reaches for when a seat cannot answer: it never bets
    (it passes, declines or stops the mus), it always declares the truth, and
    it discards the cards its own keep rule would not keep. Deterministic, and
    it reads the table without changing it. None when `legal_actions(seat)` is
    empty, which includes every seat that is not on turn.
    """
    legal = table.legal_actions(seat)
    if not legal:
        return None
    if table.phase == Phase.MUS_REQUEST:
        return {"action": "no"}
    if table.phase == Phase.MUS_DRAW:
        return {"action": "discard",
                "cards": [str(card) for card in _toss(table.hands[seat])]}
    if table.phase == Phase.DECLARE:
        return {"action": table.declaration_of(seat)}
    if table.phase == Phase.ENVITE:
        envite = table.envite
        if envite["stake"] == 0:
            return {"action": "paso"}
        mine = envite["holder_team"] is not None \
            and envite["holder_team"] == TEAM_OF[seat]
        return {"action": "paso" if mine else "no-quiero"}
    if table.phase == Phase.ORDAGO_RESPONSE:
        return {"action": "no-quiero"}
    return None


# --------------------------------------------------------------------------
# The two reference policies
# --------------------------------------------------------------------------
#
# A policy is `policy(table, seat, legal) -> dict`: the very dict `apply`
# accepts, plus a `confidence`, which is the policy's own declared probability
# that this action is the right one. Later stages score that number, so it has
# to be a real probability and not a constant.


def random_policy(seed=0):
    """A uniform chooser over the legal actions, seeded by `seed`.

    Declarations stay truthful: the engine rejects a false tengo/no-tengo, so
    randomising them would manufacture rejections instead of games. Confidence
    is 1/len(legal) — the honest probability that a uniform chooser picks
    exactly this action.
    """
    rng = Random(seed)

    def policy(table, seat, legal):
        if table.phase == Phase.DECLARE:
            return {"action": table.declaration_of(seat), "confidence": 1.0}
        name = rng.choice(legal)
        action = {"action": name, "confidence": 1.0 / len(legal)}
        if name == "discard":
            hand = table.hands[seat]
            take = rng.randint(1, len(hand))
            action["cards"] = [str(card) for card in rng.sample(hand, take)]
        return action

    return policy


MUS_QUALITY_MAX = 0.45      # below this, ask for mus
QUIERO_MIN = 0.45           # percentile that accepts an ordago
OPEN_BID = 0.40             # percentile that opens an envido
RAISE_HIGH = 0.75           # percentile that answers a bet with a raise


def _hand_quality(hand) -> float:
    """How good a four-card hand looks before any specific lance: juego first,
    then pares, then raw Grande weight. The reference's floor, ported."""
    total = _hand_points(hand)
    juego = JUEGO_RANK.get(total, 0) / 10.0 if total in JUEGO_TOTALS else 0.0
    pares = _pares_value(hand)[0] / 3.0
    grande = sum(RANK_GRANDE[card.rank] for card in hand) / 48.0
    return 0.4 * juego + 0.35 * pares + 0.25 * grande


def heuristic_policy(seed=0):
    """A mus-aware floor: honour the mus when the hand is worth improving,
    discard the cards that cannot pay, declare the truth, and price every
    bet with `strength`.

    It never raises and never ordagos — it accepts, declines or passes — so a
    hand it plays is short on purpose; raising is left to the random policy
    and to the policies a later stage writes. The `seed` decides the ties (for
    instance which of two equally keepable cards goes), so two heuristic seats
    are not the same player twice.
    """
    rng = Random(seed)

    def policy(table, seat, legal):
        hand = table.hands[seat]

        if table.phase == Phase.MUS_REQUEST:
            quality = _hand_quality(hand)
            if quality < MUS_QUALITY_MAX:
                return {"action": "mus", "confidence": 0.5}
            return {"action": "no", "confidence": min(0.95, 0.5 + quality)}

        if table.phase == Phase.MUS_DRAW:
            toss = _toss(hand, rng)
            return {"action": "discard",
                    "cards": [str(card) for card in toss],
                    "confidence": 0.5 + 0.1 * len(toss)}

        if table.phase == Phase.DECLARE:
            return {"action": table.declaration_of(seat), "confidence": 1.0}

        percentile = strength(table, seat)

        if table.phase == Phase.ORDAGO_RESPONSE:
            if percentile >= QUIERO_MIN:
                return {"action": "quiero", "confidence": percentile}
            return {"action": "no-quiero", "confidence": 1.0 - percentile}

        if table.phase == Phase.ENVITE:
            envite = table.envite
            mine = envite["holder_team"] is not None \
                and envite["holder_team"] == TEAM_OF[seat]
            if envite["stake"] == 0:
                if percentile >= OPEN_BID:
                    return {"action": "envido", "confidence": percentile}
                return {"action": "paso", "confidence": 1.0 - percentile}
            if mine:
                return {"action": "paso", "confidence": 0.5}
            if percentile >= RAISE_HIGH and "y-yo" in legal:
                return {"action": "y-yo", "confidence": percentile}
            if percentile >= QUIERO_MIN:
                return {"action": "quiero", "confidence": percentile}
            return {"action": "no-quiero", "confidence": 1.0 - percentile}

        # Any phase a later version adds: take the engine's own default.
        fallback = default_action(table, seat)
        if fallback is None:
            raise IllegalAction(f"no legal action for seat {seat} in "
                                f"{table.phase.name}")
        fallback["confidence"] = 1.0
        return fallback

    return policy


# --------------------------------------------------------------------------
# A seeded match
# --------------------------------------------------------------------------


def _one_policy(policies, seed: int):
    """The four callables to play with: one policy for everybody, or four."""
    if policies is None:
        policy = heuristic_policy(seed)
        return (policy, policy, policy, policy)
    if callable(policies) or hasattr(policies, "act"):
        return (policies, policies, policies, policies)
    policies = tuple(policies)
    if len(policies) != 4:
        raise ValueError("policies must be one callable or four (one per seat)")
    return policies


def _act(policy, table: Table, seat: int, legal: list[str]) -> dict:
    """Call a policy: a plain callable, or an object with `.act(table, seat,
    legal)` as the reference's baseline classes have."""
    action = getattr(policy, "act", policy)(table, seat, legal)
    if not isinstance(action, dict):
        raise ValueError("a policy must return the action dict the table accepts")
    return action


def self_play(seed: int, *, hands: int = 4, policies=None,
              record_deals: bool = False) -> dict:
    """Play `hands` hands at one table seeded with `seed`.

    `policies` is one callable used by every seat, or four (one per seat); None
    means `heuristic_policy(seed)` for everybody. A callable is
    `policy(table, seat, legal) -> dict`: the action `apply` accepts, plus a
    `confidence`.

    The result, JSON-ready as it stands:

        seed, hands                     the inputs
        vacas_a, vacas_b                vacas won by each team
        hand_wins_a, hand_wins_b        hands each team won (ties count for
                                        neither)
        turns                           accepted actions in the match
        decisions                       one record per accepted decision, in
                                        order: {"turn", "hand", "seat",
                                        "phase", "action", "confidence"}
        deals                           only with record_deals: the cards each
                                        seat was dealt, hand by hand

    `turn` is the decision's index in its own hand (0-based, and equal to
    `Table.turns` before the action). `hand` is the 0-based `Table.hand_index`.
    `phase` is a `Phase` name. `action` is the dict the table accepted,
    verbatim; `confidence` is the policy's own number, verbatim.

    Two of these with the same seed and the same policies are identical, JSON
    and all — including the deals, which do not depend on how the hands are
    played.
    """
    table = Table(seed=seed)
    by_seat = _one_policy(policies, seed)
    decisions: list[dict] = []
    deals: list[dict] = []
    hand_wins = {0: 0, 1: 0}

    for _ in range(hands):
        table.deal()
        if record_deals:
            deals.append({seat: [str(card) for card in table.hands[seat]]
                          for seat in range(4)})
        while table.phase != Phase.DONE:
            seat = table.current_seat
            legal = table.legal_actions(seat)
            if not legal:
                raise IllegalAction(f"no legal action for seat {seat} in "
                                    f"{table.phase.name}")
            action = _act(by_seat[seat], table, seat, legal)
            try:
                confidence = action["confidence"]
            except (KeyError, TypeError):
                raise ValueError(
                    "a policy action must carry 'confidence' (0..1)") from None
            decisions.append({
                "turn": table.turns,
                "hand": table.hand_index,
                "seat": seat,
                "phase": table.phase.name,
                "action": action,
                "confidence": confidence,
            })
            table.apply(seat, action)
        if table.hand_winner is not None:
            hand_wins[table.hand_winner] += 1

    result = {
        "seed": seed,
        "hands": hands,
        "vacas_a": table.vacas_a,
        "vacas_b": table.vacas_b,
        "hand_wins_a": hand_wins[0],
        "hand_wins_b": hand_wins[1],
        "turns": len(decisions),
        "decisions": decisions,
    }
    if record_deals:
        result["deals"] = deals
    return result
