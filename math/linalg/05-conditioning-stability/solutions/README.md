# Solutions

Complete implementation of the conditioning / stability module. Run the demo:

```
python3 stability.py
```

Expected output (floating-point values may differ in the last digits; the
qualitative points must not):

```
norm_inf([[1,2,3],[4,5,6],[7,8,10]]) = 25.0
condition number of I_4            = 1.0
condition number of Hilbert 8x8    = 3.387e+10

growth factor under partial pivoting
  wilkinson_growth(3): growth = 4.0  (2^(n-1) = 4)
  wilkinson_growth(4): growth = 8.0  (2^(n-1) = 8)
  wilkinson_growth(5): growth = 16.0  (2^(n-1) = 16)
  wilkinson_growth(6): growth = 32.0  (2^(n-1) = 32)

limit case A = [[1e-18, 1], [1, 1]], x_true = [1, 1]
  no pivot : x = [0.0, 1.0]  forward error = 1.000e+00
  pivot    : x = [1.0, 1.0]  forward error = 0.000e+00

max forward / (condition * backward) over 100 random 6x6 systems =
  0.042553
```

The last line being below 1 is the empirical form of
`forward <= condition * backward`: partial pivoting is backward stable, so the
forward error is controlled entirely by the problem's conditioning.

The whole checker passes against this file:

```
cd <temporary copy containing stability.py and check.py>
python3 check.py --all
# 5/5 passing
```
