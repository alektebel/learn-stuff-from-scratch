import pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2] / "week-02" / "autograd"
BUGS = [
 (1, "tensor.py", "matmul with the inner loops transposed",
  "                for j in range(n):\n                    data[out_row + j] += scale * b[b_row + j]",
  "                for j in range(n):\n                    data[out_row + j] += scale * b[j * k + p if j * k + p < len(b) else 0]"),
 (2, "tensor.py", "matmul backward uses B instead of B-transpose",
  "                        for j in range(n):\n                            total += g[g_row + j] * b[b_row + j]",
  "                        for j in range(n):\n                            total += g[g_row + j] * b[(j * k + p) % len(b)]"),
 (2, "tensor.py", "tanh backward forgets the 1 - t^2",
  "            self.accumulate([g * (1 - d * d) for g, d in zip(out.grad, data)])",
  "            self.accumulate([g * d for g, d in zip(out.grad, data)])"),
 (3, "tensor.py", "gradients assigned rather than accumulated",
  '''        if self.grad is None:
            self.grad = list(gradient)
        else:
            for i, value in enumerate(gradient):
                self.grad[i] += value''',
  "        self.grad = list(gradient)"),
 (3, "tensor.py", "broadcast gradient never folded back",
  '''    folded = [0.0] * _numel(target)
    for i, value in enumerate(gradient):
        folded[index_map(i)] += value
    return folded''',
  "    return gradient[:_numel(target)]"),
 (4, "tensor.py", "softmax without the max subtraction",
  "            biggest = max(row)                       # stability",
  "            biggest = 0.0"),
 (4, "tensor.py", "cross-entropy gradient misses the one-hot subtraction",
  "            for r in range(rows):\n                gradient[r * cols + targets[r]] -= scale",
  "            pass"),
 (5, "nn.py", "parameters() does not recurse into a list of modules",
  '''            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, Module):
                        found.extend(item.parameters())''',
  '''            elif isinstance(value, (list, tuple)):
                for item in value:
                    if False:
                        found.extend(item.parameters())'''),
 (5, "nn.py", "He init without the factor of two",
  '        return math.sqrt(2.0 / fan_in)',
  '        return math.sqrt(1.0 / fan_in)'),
 (6, "nn.py", "dropout without the 1/keep rescale",
  "        mask = Tensor([(1.0 / keep) if self.rng.random() < keep else 0.0",
  "        mask = Tensor([1.0 if self.rng.random() < keep else 0.0"),
 (6, "nn.py", "train_mode misses a Dropout inside a Sequential",
  '''    if isinstance(module, Dropout):''',
  '''    if False:'''),
 (7, "optim.py", "momentum decays instead of accumulating",
  "                    velocity[i] = self.momentum * velocity[i] + g",
  "                    velocity[i] = g"),
 (7, "optim.py", "Adam without bias correction",
  "        correction1 = (1 - self.beta1 ** t) if self.bias_correction else 1.0\n"
  "        correction2 = (1 - self.beta2 ** t) if self.bias_correction else 1.0",
  "        correction1 = 1.0\n        correction2 = 1.0"),
 (8, "optim.py", "clipping applied per tensor, changing the direction",
  '''    total = 0.0
    for parameter in parameters:
        if parameter.grad:
            total += sum(g * g for g in parameter.grad)
    norm = math.sqrt(total)''',
  '''    norm = 0.0
    for parameter in parameters:
        if parameter.grad:
            norm = max(norm, math.sqrt(sum(g * g for g in parameter.grad)))'''),
 (9, "train.py", "the loop never zeroes gradients",
  "            optimizer.zero_grad()\n            logits = model(Tensor.from_rows(batch_x))",
  "            logits = model(Tensor.from_rows(batch_x))"),
 (9, "train.py", "accuracy measured with argmin",
  "            if scores.index(max(scores)) == target:",
  "            if scores.index(min(scores)) == target:"),
 (10, "generative.py", "reparameterize forgets the sqrt on the variance",
  "        return mu + (log_var * 0.5).exp() * eps",
  "        return mu + log_var.exp() * eps"),
 (10, "generative.py", "the KL term is never added to the loss",
  "        return recon_loss + kl * beta, recon_loss.item(), kl.item()",
  "        return recon_loss, recon_loss.item(), kl.item()"),
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
            failures.append(f"[{step}] {label}: patch did not apply")
            continue
        target.write_text(text.replace(old, new, 1))
        result = subprocess.run([sys.executable, "check.py", str(step)],
                                cwd=work, capture_output=True, text=True,
                                timeout=600)
        caught = "✗" in result.stdout
        print(f"  step {step:>2}  {'caught' if caught else 'MISSED':<7} {label}")
        if not caught:
            failures.append(f"[{step}] {label}\n{result.stdout}")

print()
if failures:
    print("PROBLEMS:")
    for f in failures:
        print(" ", f[:400])
    sys.exit(1)
print(f"all {len(BUGS)} injected bugs were caught")
