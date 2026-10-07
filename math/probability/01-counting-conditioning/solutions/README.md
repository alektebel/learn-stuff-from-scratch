# Counting & Conditioning From Scratch — Solutions

A complete version of the template in the parent directory. Pure Python 3, no
dependencies. Run it from the module directory:

```bash
python3 solutions/probability.py
```

Expected output (Monte-Carlo numbers are seeds-fixed; the exact values never change):

```
Counting & conditioning from scratch — exact vs 10^5-trial simulation
  two pair                   exact 0.0475  sim 0.0472  gap 0.0004  4SE 0.0027  ok
  at least one ace           exact 0.3412  sim 0.3397  gap 0.0015  4SE 0.0060  ok
  base rate                  prevalence 1.00%  sensitivity 95%  specificity 90%
  diagnostic posterior       P(disease | +) = 0.0876   (the intuitive answer is the sensitivity, 0.95)
  diagnostic posterior       exact 0.0876  sim 0.0896  gap 0.0020  4SE 0.0036  ok
  Monty Hall
    knowing host, stay       exact 0.3333  sim 0.3347  gap 0.0014  4SE 0.0060  ok
    knowing host, switch     exact 0.6667  sim 0.6653  gap 0.0014  4SE 0.0060  ok
    unknowing host, stay     exact 0.5000  sim 0.5030  gap 0.0030  4SE 0.0063  ok
    unknowing host, switch   exact 0.5000  sim 0.4970  gap 0.0030  4SE 0.0063  ok
```

Three lines carry the module:

- **two pair ≈ 0.0475**, and the exact value `198/4165` is not obvious from the four
  factors `C(13,2)·C(4,2)²·44` until they are divided by `C(52,5)`. Returning the count
  `123552` instead is the bug step 3 plants.
- **diagnostic posterior ≈ 0.0876**, against a sensitivity of `0.95`. A 1% base rate means
  the false positives (99 healthy people per 100, of whom 10% test positive) swamp the true
  positives (0.95 per 100); the posterior is 19/217, and the intuition is off by more than
  10×.
- **Monty Hall, unknowing host, switch ≈ 0.50** versus **0.67** for the knowing host. The
  host's knowledge, not the act of switching, is what transfers probability to the last
  closed door. The simulation discards rounds where the unknowing host reveals the car
  before it conditions.

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd math/probability/01-counting-conditioning
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 9/9 passing
```
