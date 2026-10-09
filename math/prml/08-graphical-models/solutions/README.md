# solutions

The reference implementation of `math/prml/08-graphical-models`. This directory is for
the learner to compare against, and for `check.py` to be graded against.

```bash
cd solutions
python3 graphical.py       # the demo
```

Expected output (`python3 graphical.py`):

```text
Graphical models: d-separation, sum-product and max-sum
  chain A->B->C: d-sep(A,C|{})=False , d-sep(A,C|{B})=True
  common cause A<-B->C: d-sep(A,C|{})=False , d-sep(A,C|{B})=True
  collider A->C<-B: d-sep(A,B|{})=True , d-sep(A,B|{C})=False
  sum-product vs brute force: max error 1.67e-16
  max-sum {'A': 0, 'B': 0, 'C': 0} -> P=0.3780 (brute-force best P=0.3780)
  MC independence chain(A,C|{}): 0.0714
  triangle loopy BP: converged=False , max marginal gap vs brute force 3.60e-01
```

To grade the reference, put `check.py` and the reference `graphical.py` in one directory
and run there:

```bash
mkdir /tmp/prml08-check && cp check.py solutions/graphical.py /tmp/prml08-check/
cd /tmp/prml08-check && python3 check.py --all
```

`check.py` never imports this directory. It carries its own hand-built DAGs, its own
full-joint enumeration, its own random-tree generator, its own ancestral sampler and its
own triangle model, so a passing run means the *learned* code agrees with arithmetic done
independently of it.
