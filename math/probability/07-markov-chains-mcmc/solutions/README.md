# Solutions

A complete, pure-standard-library implementation of
`math/probability/07-markov-chains-mcmc`. Run it as a script to see the
measurements the node promises:

```bash
cd math/probability/07-markov-chains-mcmc/solutions
python3 mcmc.py
```

## Expected demo output

```
Stationary distributions (left eigenvector of P, by elimination)
  2-state P = [[0.5, 0.5], [0.25, 0.75]]
    pi = [0.333333, 0.666667]
  3-state P = [[0.5, 0.25, 0.25], [0.5, 0.0, 0.5], [0.25, 0.25, 0.5]]
    pi = [0.4, 0.2, 0.4]
Periodic chain [[0,1],[1,0]]: stationary but never converges
  pi                    = [0.5, 0.5]
  P^50 (even)           = [[1.0, 0.0], [0.0, 1.0]]
  P^51 (odd)            = [[0.0, 1.0], [1.0, 0.0]]
Empirical distribution of a 100000-step chain
  empirical = [0.3996, 0.1992, 0.4012]
  pi        = [0.4, 0.2, 0.4]
Metropolis-Hastings on a standard normal
  sample mean = -0.0125   (target 0.0)
  sample var  = 0.9990   (target 1.0)
Gibbs sampling on a 2-D normal (rho = 0.7)
  mean(x), mean(y) = 0.0046, 0.0056
  var(x), var(y)   = 0.9929, 0.9973
  corr(x, y)       = 0.6984
Bimodal target: tiny step versus large step
  step 0.02: fraction left = 1.0000, right = 0.0000
  step  8.0: fraction left = 0.4924, right = 0.5076
```

The numbers after the first five lines come from seeded `random.Random`
generators, so they reproduce exactly. The last two lines are the limit case:
a step of `0.02` on a target whose two modes are `8` apart never crosses, and
the run is a point mass on the left mode; a step of `8` crosses freely and both
modes are visited.

## How the acceptance rule is met

The stationary distributions are exact to elimination: `(1/3, 2/3)` for the
2-state chain and `(0.4, 0.2, 0.4)` for the 3-state chain. A 100000-step
simulation of the 3-state chain reproduces `(0.4, 0.2, 0.4)` to three decimals
-- this is the node's acceptance criterion, the empirical distribution of a
long chain matching `pi`. Metropolis-Hastings on a standard normal recovers mean
`0` and variance `1`; on `N(2, 1.5^2)` it recovers `2` and `2.25`. Gibbs on a
2-D normal with correlation `0.7` recovers zero means, unit variances and
correlation `0.70`.

## Running the checker against this solution

`check.py` sits one level up and never imports this directory. Copy these
solutions next to it in a scratch directory:

```bash
tmp=$(mktemp -d)
cp mcmc.py ../check.py "$tmp"/
( cd "$tmp" && python3 check.py --all )
```

All five steps pass. To see what a learner sees, run `python3 ../check.py
--all` in the module directory (the template there reports every step as TODO).
