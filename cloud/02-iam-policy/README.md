# IAM Policy Evaluator From Scratch

Implement the core of AWS IAM's authorisation decision in pure Python: parse a policy
document, match actions and resources with wildcards, evaluate conditions against a
request context, and decide Allow or Deny by the documented rule.

Source: AWS docs, *IAM policy evaluation logic* (`awsiam:evaluation`), specifically
[How AWS enforcement code logic evaluates requests to allow or deny access](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html),
and *IAM JSON policy elements: Condition operators* for the operator semantics.

## The rule

The whole engine is three lines, and the first one is the one people get wrong:

```
1. An explicit DENY anywhere always wins.
2. Otherwise, an explicit ALLOW grants access.
3. Otherwise, DENY — the implicit default.
```

Everything else — wildcards, conditions, NotAction, permissions boundaries — is
detail hung off those three lines. A firewall lets the last matching rule win; IAM
does not. Policies are a **set**: moving a statement or reordering the policies can
never change the answer, which is the property `check.py` tests directly.

## How to use this directory

The files at the top level are **templates**: each function carries a docstring
explaining what to build and why, then `raise NotImplementedError`. `solutions/`
holds complete, runnable versions for when you are stuck or want to compare.

```bash
cd cloud/02-iam-policy
python3 check.py            # what to build next
# ... implement the functions the checker points at ...
python3 check.py            # re-run; it stops at the first thing not yet done
python3 <file>.py           # run that file's own demo once it works
```

`check.py` runs **9 graded checks** against **your** code (it never imports
`solutions/`). Each names the file, the concept, and — when something is wrong — the
likely cause:

```
  ✓  1. conditions.py  operator table: string, bool, IP, numeric, ARN
  ·  3. policy.py      parse a policy document (dict and JSON)
      not implemented yet — parse_policy
```

| Command | Does |
|---|---|
| `python3 check.py` | Run in order, stop at the first unimplemented step |
| `python3 check.py 4` | Run only step 4, while you iterate on it |
| `python3 check.py 4 6` | Run steps 4 through 6 |
| `python3 check.py --all` | Run everything, skipping nothing |

A grey `·` is a TODO. A red `✗` is a failure and the message says how. Work top to
bottom: `policy.py` imports `conditions.py`.

## Learning path

### 1. `conditions.py` — the `Condition` element

`condition_holds` is an operator table; `evaluate_condition` is the logic around it.
Two rules to internalise:

- **AND across keys, OR within one key's value list.** Two `StringEquals` keys must
  *both* hold; two values under one key mean *either* will do. The asymmetry is the
  thing people get wrong.
- **A missing context key fails closed.** A key the policy names but the request does
  not carry cannot satisfy the condition, so the statement does not apply. This is
  where the deliberate simplification lives — see *Where this stops*.

Operators: `StringEquals`, `StringEqualsIgnoreCase`, `StringLike` (+ negated forms),
`Bool`, `IpAddress`, `NotIpAddress`, `Numeric*`, `ArnLike`/`ArnEquals` (+ negated),
and `Null` (existence). Unknown operators raise rather than pass.

### 2. `policy.py` — parse, match, evaluate

`parse_policy` turns a JSON document into `Statement`/`Policy` objects; `matches_action`
and `matches_resource` implement the wildcard rules; `statement_matches` combines
action ∧ resource ∧ condition; `evaluate` is the three-line rule.

The `__main__` demos in both files print the behaviour — run them and predict each
line before you look.

## Design decisions

**Evaluate in order, or partition by effect?** Firewall-style order is what people
expect. *Chosen:* partition by effect — collect matching Deny, then matching Allow —
because that is what makes order irrelevant, and order-irrelevance is what lets a
human reason about a policy set at all. The cost: you cannot write "deny then allow"
as an override, and a second Deny is silently a no-op.

**Wildcards: `fnmatch`, or hand-written?** `fnmatch` implements IAM's `*`/`?` exactly,
but `fnmatch.fnmatch` case-folds through `os.path.normcase` — a no-op on Linux,
case-insensitive on Windows. A platform-dependent security decision is unacceptable,
so the code uses `fnmatchcase` everywhere and lower-cases both sides *only* for
actions, making the case rules explicit: actions are case-insensitive, ARNs are
case-sensitive.

**Conditions: an operator table or a grammar?** The real language has ~40 operators,
set qualifiers, policy variables and date math. *Chosen:* a flat table, honest about
what it supports; an unknown operator raises instead of silently passing. The cost is
no `ForAllValues`/`ForAnyValue`, no `...IfExists`, no policy variables.

**Negated operators over a list: OR or AND?** `StringEquals` ORs the list;
`StringNotEquals` with `["b", "c"]` reads as "neither", which is AND. The code makes
that rule data (`NEGATED_OPERATORS`) rather than something to remember.

## Questions to answer from the material (no answers here)

1. `evaluate` returns on the *first* matching Deny but keeps looking for Allows. Why
   is it safe to return early on Deny but not on Allow? What would break if you
   returned on the first Allow?
2. `arn:aws:s3:::bucket/*` matches `arn:aws:s3:::bucket/a/b/c`. Write down the exact
   set of resources it matches. Now: what does `arn:aws:s3:::bucket` (no `/*`) match?
3. The condition below allows an action only when both keys hold. Which single line
   would you delete to make it accept a request missing `aws:SourceIp`, and why is
   that a security bug?

   ```json
   {"StringEquals": {"aws:username": "alice"},
    "IpAddress":    {"aws:SourceIp": "10.0.0.0/8"}}
   ```
4. Why must `Null` be evaluated *before* the missing-key check in
   `evaluate_condition`, rather than as a normal operator in `condition_holds`?
5. Eight Allow statements and one Deny all match. State which one decides the request
   and why the count of Allows is irrelevant.

## Mutation table

`python3 .claude/skills/graded-module/scripts/mutate.py cloud/02-iam-policy cloud/02-iam-policy/_build/mutations.py`
plants each bug below into a copy of the solutions and requires the named check to
catch it. All 8 are **CAUGHT**.

| # | Bug planted | File | Step |
|---|---|---|---|
| 1 | `Bool` compared as a string (`True == "true"`) | `conditions.py` | 1 |
| 2 | Unknown condition operator returns `True` instead of raising | `conditions.py` | 1 |
| 3 | A missing key slips through a negated operator (`str(None) != "bob"`) | `conditions.py` | 2 |
| 4 | A single `Statement` object is iterated key-by-key, not wrapped | `policy.py` | 3 |
| 5 | Action matching is case-sensitive | `policy.py` | 4 |
| 6 | Resource matching ignores wildcards (`resource == pattern`) | `policy.py` | 5 |
| 7 | Explicit Deny no longer wins — an Allow overrides it | `policy.py` | 7 |
| 8 | The implicit default becomes Allow | `policy.py` | 9 |

## Where this stops

- **One account, identity policies only.** Resource-based policies, permissions
  boundaries, SCPs/RCPs and session policies each add another layer of intersection
  or union; the toy `evaluate` stops at the identity layer. [`aws-from-scratch/`](../../aws-from-scratch/)
  sketches boundaries and STS on the same three rules.
- **Missing-key behaviour is stricter than AWS.** The docs make a negated operator
  (`StringNotLike`, `ArnNotLike`) *true* when the key is absent; this implementation
  fails closed for every operator. Safer, simpler, and stated here so you do not carry
  it into production.
- **No set operators, no `...IfExists`, no policy variables** (`${aws:username}`), no
  `Principal` / cross-account evaluation, no `NotResource`.
- **No policy size limits or validation.** Real IAM rejects a policy over its size
  budget or with a malformed `Condition`; this parses whatever JSON it is given.

## Structure

```
cloud/02-iam-policy/
├── README.md
├── check.py              # progress checker — run this first
├── conditions.py         # templates with TODOs
├── policy.py
├── _build/
│   ├── hints.py
│   └── mutations.py
└── solutions/            # complete, runnable implementations
```

Pure Python 3 standard library. No dependencies. `python3 check.py` runs in well under
a second.

## Related directories

- [`aws-from-scratch/`](../../aws-from-scratch/) — the broader AWS surface: IAM
  boundaries and STS, plus S3, SQS, DynamoDB, Lambda, SNS, KMS and VPC
- [`database-from-scratch/`](../..//database-from-scratch/) — the canonical stdlib-only
  graded module this one's checker is modelled on
