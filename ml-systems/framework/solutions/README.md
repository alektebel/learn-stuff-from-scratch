# Framework from scratch — solutions

```bash
python3 tensor.py    # one forward/backward through a tiny graph
python3 train.py     # the three milestones and the spirals (about 3 s)
python3 costs.py     # parameters, FLOPs and Adam memory of a 784-512-512-10 MLP
```

Expected `train.py` output:

```
1958 perceptron on separable blobs: 1.000
1969 perceptron on XOR:             0.634  (cannot do better than ~0.75)
1986 MLP on XOR:                    1.000
     MLP on 3 spirals:              0.993  (loss 0.80 -> 0.026)
```
