# Task suite

Twenty tasks. `targets` names the mechanisms a task is built to exercise (amendment 2).
Every task has a reference solution; the oracle agent proves each one passable and the null agent
proves each verifier fails on the untouched repo.

| id | category | targets | earlier turns | generated repo |
|---|---|---|---|---|
| `t01-pagination` | bugfix | baseline |  |  |
| `t02-mutable-default` | bugfix | baseline |  |  |
| `t03-split-amount` | bugfix | baseline |  |  |
| `t04-config-merge` | bugfix | baseline |  |  |
| `t05-misleading-symptom` | bugfix | baseline, root-cause |  |  |
| `t06-slugify` | feature | baseline |  |  |
| `t07-lru-cache` | feature | baseline |  |  |
| `t08-cli-subcommand` | feature | baseline |  |  |
| `t09-retry-decorator` | feature | baseline |  |  |
| `t10-extract-validation` | refactor | baseline, edit-precision |  |  |
| `t11-rename-with-alias` | refactor | baseline, multi-edit |  |  |
| `t12-global-state` | refactor | baseline |  |  |
| `t13-refund-totals` | multifile | code-navigation, read-many-files |  |  |
| `t14-propagate-field` | multifile | read-many-files, multi-edit |  |  |
| `t15-session-constraint` | recall | long-session-recall, compaction | 4 | yes |
| `t16-superseded-instruction` | recall | long-session-recall, memory-supersession | 4 | yes |
| `t17-large-repo` | limit | repo-map, search, context-overflow |  | yes |
| `t18-oscillating-fix` | limit | stuck-detection, loop-detection, reflection |  |  |
| `t19-huge-log` | limit | tool-output-truncation, compaction, context-overflow |  | yes |
| `t20-hidden-edge-cases` | limit | verify-on-stop, reflection, self-testing |  |  |
