# IAM Policy Evaluator — Solutions

Complete versions of every template in the parent directory. Pure Python 3, no
dependencies. Run them from inside this directory (the files import each other by name):

```bash
python3 conditions.py   # the operator table, AND/OR, fail-closed, Null
python3 policy.py       # the three-line rule, conditions, eight Allows and a Deny
```

## Expected output

`conditions.py`:

```
=== The operator table ===
  StringEquals          us-east-1                   ['us-east-1']                 True
  StringLike            s3:GetObject                ['s3:Get*']                   True
  StringNotEquals       prod                        ['dev', 'staging']            True
  Bool                  True                        ['true']                      True
  IpAddress             10.1.2.3                    ['10.0.0.0/8']                True
  IpAddress             203.0.113.9                 ['10.0.0.0/8']                False
  NumericLessThan       10                          ['100']                       True
  ArnLike               arn:aws:iam::111:user/dev   ['arn:aws:iam::111:user/*']   True
  unknown operator raises: True

=== AND across keys, OR within one ===
  alice, in 10/8            True
  alice, in 192.168/16      True
  bob, in 10/8              False
  alice, no SourceIp        False
  empty context             False

=== Null asks about existence, not value ===
  absent, Null=true               True
  present, Null=true              False
  present, Null=false             True
```

`policy.py`:

```
=== The three-line rule ===
  s3:GetObject    arn:aws:s3:::reports/q1.csv     ALLOW  explicit Allow
  s3:PutObject    arn:aws:s3:::reports/q1.csv     DENY   implicit Deny — no statement allows this
  s3:GetObject    arn:aws:s3:::secrets/key.pem    DENY   implicit Deny — no statement allows this

=== Explicit Deny beats an unconditional Allow ===
  admin alone                   ALLOW  explicit Allow
  admin + guardrail             DENY   explicit Deny (NoDeletes) in policy Guardrail
  guardrail + admin (swapped)   DENY   explicit Deny (NoDeletes) in policy Guardrail
  Order does not matter: policies are a set, not a rule list.

=== Conditions gate a statement ===
  in VPC, TLS           ALLOW  explicit Allow
  in VPC, no TLS        DENY   implicit Deny — no statement allows this
  outside, TLS          DENY   implicit Deny — no statement allows this
  TLS, no SourceIp      DENY   implicit Deny — no statement allows this
  Conditions AND across keys, OR within one, and fail closed when a
  context key is missing — the last row is a Deny, not 'unknown'.

=== Eight Allows and one Deny ===
  allowed without the Deny: True
  with the Deny appended:   DENY   explicit Deny in policy ManyAllows
```

## Implementation notes — the traps this file fell into

- **`fnmatch.fnmatch` is not `fnmatchcase`.** `fnmatch` case-folds through
  `os.path.normcase`, which is a no-op on Linux and case-insensitive on Windows. An
  authorisation decision must not depend on the host OS, so both matchers use
  `fnmatchcase` and the action matcher lower-cases both sides itself.
- **A missing key with `str(None)`.** The first version of `evaluate_condition` skipped
  the presence check and compared `str(context.get(key))` directly. For a positive
  operator that happens to be safe (`"None" != "alice"`), but for a negated one it
  silently matches — `"None" != "bob"` is `True` — so a `StringNotEquals` condition
  applied to a request that never carried the key. The fix is to reject absent keys
  before calling `condition_holds`; the mutation tester catches the regression.
- **`Bool` is not a string.** `aws:SecureTransport` is a Python `bool` in the request
  context but `"true"` in the policy JSON. Comparing them as strings is always False,
  so a TLS-only statement never applies. `condition_holds` coerces with
  `bool(actual) == (option.lower() == "true")`.
- **A single `Statement` object.** IAM accepts both `"Statement": {...}` and
  `"Statement": [{...}]`. Treating the dict as an iterable walks its *keys* and then
  indexes a string with `[...]`. `parse_policy` wraps a dict in a one-element list.
- **Return on Deny, collect Allow.** Returning on the first matching statement is the
  firewall habit. It is safe for Deny (nothing overrides it) and wrong for Allow
  (a later Deny must still win), so Allows are collected as a boolean and only
  consulted after the whole set is scanned.
