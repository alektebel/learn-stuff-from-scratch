import pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2] / "week-02" / "llm-from-scratch"
BUGS = [
 (1, "tokenizer.py", "merges the LEAST frequent pair",
  "            best, frequency = pairs.most_common(1)[0]",
  "            best, frequency = pairs.most_common()[-1]"),
 (2, "tokenizer.py", "merges left-to-right instead of by rank",
  "            _, position = min(candidates)",
  "            _, position = min(candidates, key=lambda c: c[1])"),
 (2, "tokenizer.py", "decode drops the leading space",
  '        return "".join(self.inverse.get(index, "") for index in ids)',
  '        return "".join(self.inverse.get(index, "").lstrip() for index in ids)'),
 (3, "attention.py", "no sqrt(d_k) scaling",
  "    scores = (q @ k.transpose()) * (1.0 / math.sqrt(d_k))",
  "    scores = q @ k.transpose()"),
 (3, "attention.py", "no causal mask",
  "    weights = masked_softmax(scores, mask or [[True] * length\n"
  "                                              for _ in range(length)])",
  "    weights = masked_softmax(scores, [[True] * length\n"
  "                                      for _ in range(length)])"),
 (4, "attention.py", "every head reads the same slice",
  "            lo, hi = head * self.head_dim, (head + 1) * self.head_dim",
  "            lo, hi = 0, self.head_dim"),
 (5, "engine.py", "layer norm divides by variance not its root",
  "        inverse = 1.0 / math.sqrt(variance + eps)",
  "        inverse = 1.0 / (variance + eps)"),
 (5, "transformer.py", "weight tying does not actually tie",
  '''        self.head = (None if tie_weights
                     else Linear(d_model, vocab_size, activation="linear",
                                 bias=False, rng=rng))''',
  '''        self.head = Linear(d_model, vocab_size, activation="linear",
                           bias=False, rng=rng)'''),
 (6, "transformer.py", "positional embedding never added",
  "        if self.positional:\n            x = x + embedding(self.position_embedding, list(range(len(ids))))",
  "        if False:\n            x = x + embedding(self.position_embedding, list(range(len(ids))))"),
 (7, "train.py", "optimizer steps inside the accumulation loop",
  '''            loss.backward()
            total += loss.item()
        for parameter in model.parameters():''',
  '''            loss.backward()
            optimizer.zero_grad()
            total += loss.item()
        for parameter in model.parameters():'''),
 (7, "transformer.py", "loss predicts the same token instead of the next",
  "        return logits.softmax_cross_entropy(list(ids[1:]))",
  "        return logits.softmax_cross_entropy(list(ids[:-1]))"),
 (8, "sample.py", "temperature applied to probabilities, not logits",
  '''    scaled = [v / temperature for v in logits]
    biggest = max(scaled)
    exponentials = [math.exp(v - biggest) for v in scaled]
    total = sum(exponentials)
    return [v / total for v in exponentials]''',
  '''    biggest = max(logits)
    exponentials = [math.exp(v - biggest) for v in logits]
    total = sum(exponentials)
    raw = [v / total for v in exponentials]
    adjusted = [v / temperature for v in raw]
    scale = sum(adjusted)
    return [v / scale for v in adjusted]'''),
 (8, "sample.py", "top_p keeps a fixed number, like top_k",
  '''        if cumulative >= p:
            break''',
  '''        if size >= 3:
            break'''),
 (8, "sample.py", "top_k forgets to renormalise",
  '''    kept = [p if p >= threshold else 0.0 for p in probabilities]
    total = sum(kept)
    return [p / total for p in kept]''',
  '''    return [p if p >= threshold else 0.0 for p in probabilities]'''),
]
failures = []
for step, filename, label, old, new in BUGS:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "s"
        shutil.copytree(ROOT / "solutions", work,
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "check.py", work / "check.py")
        target = work / filename
        text = target.read_text()
        if old not in text:
            print(f"  step {step:>2}  PATCH-FAIL {label}")
            failures.append(f"[{step}] {label}: patch did not apply"); continue
        target.write_text(text.replace(old, new, 1))
        r = subprocess.run([sys.executable, "check.py", str(step)], cwd=work,
                           capture_output=True, text=True, timeout=600)
        caught = "✗" in r.stdout
        print(f"  step {step:>2}  {'caught' if caught else 'MISSED':<7} {label}")
        if not caught:
            failures.append(f"[{step}] {label}\n{r.stdout[:300]}")
print()
if failures:
    print("PROBLEMS:")
    for f in failures: print(" ", f)
    sys.exit(1)
print(f"all {len(BUGS)} injected bugs were caught")
