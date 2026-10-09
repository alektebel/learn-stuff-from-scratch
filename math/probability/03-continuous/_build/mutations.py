"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

One classic mistake per mechanism, each an exact edit to a copy of the
solutions. Every mutation must be CAUGHT by the step named; a MISSED mutation
means the check is too weak, never that the bug is acceptable.

The five the node names: the KS statistic with the wrong ECDF convention, the
Normal quantile returning the CDF, memorylessness asserted on a shifted
variable, the KS p-value truncated after its first term, and the tail-truncation
case claiming accuracy while hiding the missing quantile. The sixth pins the
exponential inverse, so step 1 is mutation-covered too.
"""
MUTATIONS = [
    # Exponential quantile with the wrong inverse: -ln(u) instead of -ln(1-u).
    ("exponential ppf uses -ln(u) instead of -ln(1-u)", "continuous.py",
     "    return -math.log1p(-u) / rate\n",
     "    return -math.log1p(u) / rate\n", "1"),
    # Normal quantile returns Phi(x) at the bisected x: the CDF, not its inverse.
    ("normal ppf returns the CDF instead of the inverse", "continuous.py",
     "    return 0.5 * (lo + hi)\n",
     "    return normal_cdf(0.5 * (lo + hi))\n", "2"),
    # KS statistic forgets the left limit: i/n on both sides, not (i-1)/n.
    ("KS statistic uses i/n on both sides (drops the (i-1)/n left limit)",
     "continuous.py",
     "        d = max(d, i / n - f, f - (i - 1) / n)\n",
     "        d = max(d, i / n - f, f - i / n)\n", "4"),
    # KS p-value keeps only the first term of the alternating series.
    ("KS p-value truncated to its first term (not a probability)",
     "continuous.py",
     "        if term < 1e-12:\n            break\n",
     "        if True:\n            break\n", "5"),
    # The shifted exponential is (wrongly) treated as memoryless: the shift is
    # dropped from the unconditional survival, making the gap 0.
    ("memorylessness asserted on a shifted variable", "continuous.py",
     "    return conditional - _shifted_survival(rate, shift, t)\n",
     "    return conditional - _shifted_survival(rate, 0.0, t)\n", "6"),
    # The truncation demo claims a finite missing quantile, hiding the tail.
    ("tail truncation hides the missing quantile", "continuous.py",
     '        "missing_quantile": math.inf if math.isfinite(x) else 0.0,\n',
     '        "missing_quantile": 0.0,\n', "7"),
]
