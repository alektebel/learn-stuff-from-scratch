# Variant cards

One file per variant, `<harness>-<mechanism>.md`, written before the variant's code:

- **Replicates:** the mechanism, in one paragraph.
- **Source:** repository, file path and commit read; or "based on the paper's description, not
  verified in code". Claude Code variants: paper and public documentation only.
- **Differences from the original:** everything that changes because it now runs on a shared core
  (prompts, model, tool set). This is where the transplant confound is made explicit.
- **Tasks that trigger it:** ids from `eval/tasks` whose `targets` cover this mechanism. None means
  any null result for this variant is uninformative.
- **Incompatible with:** other variants it cannot be combined with, and why.
