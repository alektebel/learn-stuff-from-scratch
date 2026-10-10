"""tiny_env.py — the PROVIDED environment. Do not edit; it has no TODOs.

A harness is a runtime around a model call, and this file is everything around
it that is not the exercise: a tiny warehouse you can query, the four analytic
tasks the course grades, the question templates its data generator samples, a
clock you can move by hand, and a model that replays a script instead of calling
anybody.

It is deterministic on purpose. The dataset is a literal, SQLite answers the same
way every run, every task's gold answer is unique (the course asserts it), and
the model is a list of turns. So a check can say "the harness asked the model for
a fourth turn, and the text it streamed was not repeated across the retry" and
mean it.

Three failure types, three owners:

    EnvError      the WORLD said no    (bad SQL, an unknown table, a write)
    ModelError    the MODEL said no    (rate limit, timeout, a truncated stream)
    HarnessError  the HARNESS is wrong (a stream with no end, an orphaned pair)

Only the last one is a bug in your code. The other two are outcomes a harness has
to carry: a query the warehouse refuses is an observation the model reads, and a
model call that times out is a retry, not a crash.
"""

import sqlite3

# --------------------------------------------------------------------------
# The three failure types
# --------------------------------------------------------------------------


class EnvError(Exception):
    """The warehouse refused: bad SQL, an unknown table, or a write."""


class ModelError(Exception):
    """The model call failed. `retryable` is the provider's opinion, and a
    harness that ignores it either retries a permanent failure forever or gives
    up on a rate limit that would have cleared."""

    def __init__(self, message, *, retryable=False):
        super().__init__(message)
        self.message = message
        self.retryable = bool(retryable)


class HarnessError(Exception):
    """The harness met something it refuses to paper over: a stream that ended
    without an `end` event, a tool result with no tool call, a message list whose
    pairs do not line up. Every one of these becomes a 400 from a real provider,
    which is why the harness fails here, where the message can say what is
    wrong."""


# --------------------------------------------------------------------------
# The warehouse
# --------------------------------------------------------------------------

SALES_COLUMNS = ("sale_id", "country", "category", "revenue")
CUSTOMER_COLUMNS = ("customer_id", "name", "country")
REGION_COLUMNS = ("region", "manager")

# Ten sales, and every "which one is highest" answer below is unique:
# furniture 490 > electronics 290 > books 170; ES 440 > CN 360 > FR 80 > DE 70.
SALES_ROWS = (
    (1, "ES", "furniture", 180.0),
    (2, "ES", "electronics", 140.0),
    (3, "ES", "furniture", 120.0),
    (4, "CN", "furniture", 160.0),
    (5, "CN", "electronics", 120.0),
    (6, "CN", "books", 80.0),
    (7, "DE", "books", 40.0),
    (8, "DE", "electronics", 30.0),
    (9, "FR", "books", 50.0),
    (10, "FR", "furniture", 30.0),
)

CUSTOMERS_ROWS = (
    (1, "Ana Ferrer", "ES"),
    (2, "Wei Zhang", "CN"),
    (3, "Lena Braun", "DE"),
)

# A table with no numeric column at all: a template that averages a column must
# not be sampled onto it, and `regions` is here so that mistake has somewhere to
# happen. `AVG(name) FROM regions` is not a harder question, it is a broken one.
REGIONS_ROWS = (
    ("ES", "Ana Ferrer"),
    ("CN", "Wei Zhang"),
    ("DE", "Lena Braun"),
)


class SQLEnv:
    """A read-only, in-memory warehouse.

    `exec` is the only door, and the only thing it returns is a result:

        {"columns": ["category", "total"], "rows": [["furniture", 490.0], ...]}

    Rows are LISTS of cells, not tuples of values, because that is what a
    database driver hands back and what every wrapper downstream has to unwrap:
    `[("furniture",)]` looks harmless until something compares it to the string
    `"furniture"`. Cells keep their SQL types; a NUMBER stays a number.
    """

    def __init__(self, sales_rows=SALES_ROWS, customers_rows=CUSTOMERS_ROWS,
                 regions_rows=REGIONS_ROWS):
        self._connection = sqlite3.connect(":memory:")
        self._connection.execute(
            "CREATE TABLE sales (sale_id INTEGER, country TEXT, category TEXT, "
            "revenue REAL)")
        self._connection.execute(
            "CREATE TABLE customers (customer_id INTEGER, name TEXT, country TEXT)")
        self._connection.executemany(
            "INSERT INTO sales VALUES (?, ?, ?, ?)", sales_rows)
        self._connection.executemany(
            "INSERT INTO customers VALUES (?, ?, ?)", customers_rows)
        self._connection.execute(
            "CREATE TABLE regions (region TEXT, manager TEXT)")
        self._connection.executemany(
            "INSERT INTO regions VALUES (?, ?)", regions_rows)

    # -- reads ------------------------------------------------------------

    def exec(self, sql):
        """Run one read. Raises EnvError for anything else (including a write:
        an analysis agent that can DROP a table is a different course)."""
        stripped = sql.strip().rstrip(";")
        lowered = stripped.lower()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise EnvError("only reads are allowed here, got: %r" % (sql.strip(),))
        try:
            cursor = self._connection.execute(stripped)
            columns = [description[0] for description in cursor.description or []]
            rows = [[cell for cell in row] for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            # The driver's message is part of the observation: a model that
            # reads "no such column: revenu" fixes its query; one that reads
            # "the query failed" asks a person.
            raise EnvError(str(exc)) from None
        return {"columns": columns, "rows": rows}

    def schema(self):
        """What a prompt can show the model, and what a generator can sample:
        every table, its columns by declared type, and which columns hold
        numbers. A question template that needs a number must not be sampled
        onto a table that has none."""
        return {
            "tables": {
                "sales": {"columns": {"sale_id": "INTEGER", "country": "TEXT",
                                      "category": "TEXT", "revenue": "REAL"},
                          "numeric": ["sale_id", "revenue"]},
                "customers": {"columns": {"customer_id": "INTEGER", "name": "TEXT",
                                          "country": "TEXT"},
                              "numeric": ["customer_id"]},
                "regions": {"columns": {"region": "TEXT", "manager": "TEXT"},
                            "numeric": []},
            },
        }

    def tables(self):
        return sorted(self.schema()["tables"])


def numeric_columns(env, table):
    """The columns of `table` whose declared type is a number — what a template
    that says AVG(...) has to check before it samples the table. `regions` has
    none, so AVG(region) FROM regions is a guaranteed failure that a generator
    must not generate — and a generator that trusts the template's `table` field
    instead of asking the schema will generate it."""
    return list(env.schema()["tables"][table]["numeric"])


# --------------------------------------------------------------------------
# The tasks the course grades
# --------------------------------------------------------------------------


class Task:
    """One analytic question, its reference query, and its gold answer.

    `kind` is "number" or "text" and it is not decoration: a verifier that
    compares `950.0` to `"950"` with `==` fails a right answer, and one that
    compares `3` to `3.0000001` with `==` fails a float that came back from a
    SUM. The gold answers here are unique — the course asserts it, because an
    answer that depends on the database's tiebreak is not a gold answer.
    """

    def __init__(self, aid, question, reference_sql, gold, kind):
        self.aid = aid
        self.question = question
        self.reference_sql = reference_sql
        self.gold = gold
        self.kind = kind

    def __repr__(self):
        return "Task(%r, %r, gold=%r)" % (self.aid, self.question, self.gold)


ANALYTIC_TASKS = (
    Task("T1", "Which category has the highest total revenue?",
         "SELECT category FROM sales GROUP BY category "
         "ORDER BY SUM(revenue) DESC LIMIT 1", "furniture", "text"),
    Task("T2", "How many sales were made in ES?",
         "SELECT COUNT(*) FROM sales WHERE country = 'ES'", 3, "number"),
    Task("T3", "Which country has the highest total revenue?",
         "SELECT country FROM sales GROUP BY country "
         "ORDER BY SUM(revenue) DESC LIMIT 1", "ES", "text"),
    Task("T4", "What is the total revenue across all sales?",
         "SELECT SUM(revenue) FROM sales", 950.0, "number"),
)


# --------------------------------------------------------------------------
# The templates a generator samples
# --------------------------------------------------------------------------

# A generated question is a template + a table (and a literal when the template
# has a hole). This is the whole generator's input: strings, and the two flags
# that say what the template needs. The course grades the sampling, the
# execution and the validation around them, not the SQL.
TEMPLATES = (
    {"name": "top_category",
     "question": "Which category has the highest total revenue?",
     "sql": "SELECT category FROM sales GROUP BY category "
            "ORDER BY SUM(revenue) DESC LIMIT 1",
     "table": "sales", "needs_number": False, "kind": "text"},
    {"name": "count_in_country",
     "question": "How many sales were made in {country}?",
     "sql": "SELECT COUNT(*) FROM sales WHERE country = '{country}'",
     "table": "sales", "needs_number": False, "kind": "number",
     "values": {"country": ["ES", "CN", "DE", "FR"]}},
    {"name": "average_of_column",
     "question": "What is the average {column} in {table}?",
     "sql": "SELECT AVG({column}) FROM {table}",
     "table": "{table}", "needs_number": True, "kind": "number"},
    # A template whose answer is NULL for a value nobody sold to: the generator
    # has to notice and drop it, or its "gold answer" is `None` and every solver
    # scores zero on a task no one can answer.
    {"name": "max_in_country",
     "question": "What is the largest single sale in {country}?",
     "sql": "SELECT MAX(revenue) FROM sales WHERE country = '{country}'",
     "table": "sales", "needs_number": True, "kind": "number",
     "values": {"country": ["ES", "ZZ"]}},
)

# The floor for a generated question: any template × table pair not in here is
# still allowed, but these four are what the course's generator must be able to
# produce without inventing SQL.
GENERATED_QUESTION_LIMIT = 200


# --------------------------------------------------------------------------
# A clock you move by hand
# --------------------------------------------------------------------------


class ManualClock:
    """The clock the harness is handed in every stage, so a check can assert a
    backoff without waiting for it. `sleep` advances the clock and records how
    long it was asked to wait: a harness that calls `time.sleep` in a retry loop
    is a harness that cannot be tested, and a check can prove it did not."""

    def __init__(self, now=0.0):
        self.time = float(now)
        self.slept = []

    def now(self):
        return self.time

    def advance(self, seconds):
        self.time += float(seconds)
        return self.time

    def sleep(self, seconds):
        self.slept.append(float(seconds))
        self.advance(seconds)
        return None

    # Surfacing the real clock is refused by design: an injected clock is the
    # only clock the harness gets.
    def time_time(self):
        raise HarnessError("the harness is given a clock, not time.time()")

    def __repr__(self):
        return "ManualClock(now=%r, slept=%r)" % (self.time, self.slept)


# --------------------------------------------------------------------------
# A model that replays a script
# --------------------------------------------------------------------------


def text_events(text, *, input_tokens=10, output_tokens=5):
    """The simplest scripted turn: some text, its usage, and the end."""
    return [{"type": "text", "text": text},
            {"type": "usage", "input_tokens": input_tokens,
             "output_tokens": output_tokens},
            {"type": "end", "reason": "stop"}]


def tool_call_events(*calls, text="", reason="tool_calls",
                     input_tokens=10, output_tokens=5):
    """A turn that ends by asking for tools: `calls` are (name, arguments)."""
    events = []
    if text:
        events.append({"type": "text", "text": text})
    for index, (name, arguments) in enumerate(calls):
        events.append({"type": "tool_call", "id": "call_%d_%s" % (index, name),
                       "name": name, "arguments": dict(arguments)})
    events.append({"type": "usage", "input_tokens": input_tokens,
                   "output_tokens": output_tokens})
    events.append({"type": "end", "reason": reason})
    return events


class ScriptedModel:
    """A model whose turns are a list. It is the only model in this course.

    Each item of `script` is one turn:

        a list of events        the turn, in order
        a callable              called with (messages, tools) and expected to
                                return an iterator of events — use it to fail
                                half way through a stream, which is exactly the
                                retry case a harness gets wrong

    `fail` is the same list one level up: a callable or an exception INSTANCE
    raised before that turn is produced, so a script can say "the first call is a
    rate limit, the second one works". A script that runs out raises a
    non-retryable ModelError: the harness asked for a turn nobody wrote, and a
    harness that turns that into a retry loop spins forever.

    `calls` is what the model was handed, `tools_seen` is the tool definitions it
    was offered — the two things a check needs to say "the second attempt re-sent
    the same messages" or "the tools were withdrawn when the run was done".
    """

    def __init__(self, script, fail=None):
        self.script = list(script)
        self.fail = list(fail or [])
        self.calls = []
        self.tools_seen = []
        self.iterators = []

    def __call__(self, messages, tools=None):
        self.calls.append([dict(message) for message in messages])
        self.tools_seen.append(tools)
        if self.fail:
            failure = self.fail.pop(0)
            failure = failure() if callable(failure) else failure
            if isinstance(failure, BaseException):
                raise failure
            self.script.insert(0, failure)
        if not self.script:
            raise ModelError(
                "the script ran out: the harness asked for turn %d and nobody "
                "scripted it" % (len(self.calls),))
        item = self.script.pop(0)
        if callable(item):
            events = item(messages, tools)
        else:
            events = item

        def replay():
            # A generator, so the caller sees events one at a time and a stream
            # can break in the middle exactly the way a real one does.
            for event in events:
                yield event
            self.iterators.append(True)

        return replay()

    @property
    def turns_left(self):
        return len(self.script)


def broken_stream(events, after, message="the stream died mid-flight"):
    """A turn that yields `after` events and then fails the way a dropped
    connection does — retryable, and already half-consumed by whoever was
    reading it."""
    def turn(messages, tools=None):
        for event in list(events)[:after]:
            yield event
        raise ModelError(message, retryable=True)
    return turn
