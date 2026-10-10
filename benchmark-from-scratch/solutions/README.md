# Solutions

Finished, runnable versions of each stage. Read them *after* attempting — a
solution read cold is just more prose, and these are short enough to fool you
into thinking the stage was easy.

| File | Stage |
|---|---|
| `stage_01.py` | The engine is the only gate, and a refusal is not a turn |
| `stage_02.py` | The match loop: what counts as a turn, and when to stop |
| `stage_03.py` | One record per turn, taken before the action landed |
| `stage_04.py` | Linking an aggression to the answer it got |
| `stage_05.py` | The reference is the hands that faced a bet, not every hand |
| `stage_06.py` | A bluff is a weak hand that bet, never a bet that lost |
| `stage_07.py` | The outcome is the piedras, and they survive the vaca reset |
| `stage_08.py` | Probe the read: Brier, log-loss, AUC, calibration |
| `stage_09.py` | Which matches may be published, and the leaderboard they build |
| `stage_10.py` | The mirrored pair: one seed, both orientations, one comparison |

The stages are cumulative: stage 2's `run_match` is stage 1's `gate` plus stage
3's `truth_snapshot`/`decision_line`; stage 5 imports stage 4's `AGGRESSIVE`;
stage 6 imports stage 4's `link_responses` and stage 5's `can_bet`,
`strength_band` and `strength_terciles`. So copying one solution over its
template needs its neighbours in place too, and `mus.py` is not a stage: it is
the domain and the reference seats, provided complete.

To compare a stage, copy it over the template and re-run the checker, then
restore the template if you want to try again:

```bash
cp solutions/stage_06.py stage_06.py
python3 codecraft/cli.py run benchmark-from-scratch
```

All ten pass their checks with the standard library alone (no numpy, no scipy —
the means, the percentiles and the ranking are written out). Four are worth
reading even if you solved them: `stage_02._take_turn` is the nineteen lines
where every counting rule in the benchmark lives; `stage_03.truth_snapshot` is
the evidence the whole analysis rests on, and its separation from
`decision_line` is the point; `stage_06.scorecard` is the stage where "a bluff is
a weak hand, not a lost bet" stops being a sentence and becomes arithmetic; and
`stage_10.paired_rows` is eleven lines that throw away exactly the number a
careless report would publish.
