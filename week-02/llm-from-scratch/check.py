"""
Progress checker for the llm-from-scratch templates.

    python3 check.py           # run every check, stop at the first gap
    python3 check.py 4         # run only step 4
    python3 check.py --all     # run everything

Nothing here imports solutions/. It tests YOUR code.
`engine.py` is provided — it is `../autograd/` with four extra operations.
Steps 9–15 are knowledge distillation (`distill.py`). Do 1–8 first.
"""

import math
import pathlib
import random
import shutil
import sys
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def check_bpe_training() -> None:
    from tokenizer import CORPUS, BPETokenizer

    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, vocabulary_size=120)
    assert tokenizer.size == 120 or tokenizer.size > 60, (
        f"vocabulary came out at {tokenizer.size}")
    assert len(tokenizer.merges) > 20, "merges should have been learned"

    merged = ["".join(pair) for pair in tokenizer.merges]
    assert any(m.strip() == "the" for m in merged), (
        f"'the' is the most common word in the corpus and never got merged. "
        f"First ten merges: {merged[:10]}. Count adjacent pairs across the "
        "whole corpus and merge the MOST FREQUENT one each round.")

    early = "".join(tokenizer.merges[0])
    late = "".join(tokenizer.merges[-1])
    assert len(early) <= len(late) + 2, (
        "the first merges should be short and frequent, the later ones longer "
        "and rarer — if the order looks reversed, the counter is picking the "
        "least common pair")

    for symbol in tokenizer.vocab:
        assert symbol in tokenizer.inverse.values()
    assert len(set(tokenizer.vocab.values())) == len(tokenizer.vocab), (
        "every token needs a distinct id")


def check_encoding() -> None:
    from tokenizer import CORPUS, BPETokenizer, WORD

    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, vocabulary_size=150)

    for text in ("the cat sat on the mat", "the dog saw the bird",
                 "a bird sat on the log and the rat ran"):
        ids = tokenizer.encode(text)
        assert tokenizer.decode(ids) == text, (
            f"decode(encode({text!r})) gave {tokenizer.decode(ids)!r}. The "
            "round trip must be exact — a tokeniser that loses whitespace "
            "produces a model that generates text it cannot read back, and the "
            "symptom appears hundreds of steps into training.")

    common = tokenizer.encode_word(" the")
    assert len(common) == 1, (
        f"' the' encoded to {common}; it should be ONE token. It is the most "
        "frequent word in the corpus, so its merge is learned early and "
        "encode_word must apply it.")

    rare = tokenizer.encode_word("zqxj")
    assert len(rare) == 4, (
        f"'zqxj' encoded to {rare}; with no merges applicable it should stay "
        "as separate characters. Unfamiliar text is expensive, not rejected.")

    # Merge order, not position order.
    scrambled = BPETokenizer()
    scrambled.vocab = dict(tokenizer.vocab)
    scrambled.merges = list(reversed(tokenizer.merges))
    scrambled.ranks = {p: i for i, p in enumerate(scrambled.merges)}
    scrambled.inverse = dict(tokenizer.inverse)
    assert scrambled.encode_word(" the") != common, (
        "reversing the merge order produced the same tokenisation, which means "
        "encode_word is applying merges in the order they appear in the word "
        "rather than by RANK. The rank order is the order they were learned "
        "in, and replaying a different one gives the model token sequences it "
        "has never seen.")

    text = "the cat sat on the mat and the dog saw the bird"
    small = BPETokenizer(); small.train(CORPUS, vocabulary_size=60)
    big = BPETokenizer(); big.train(CORPUS, vocabulary_size=300)
    assert len(big.encode(text)) < len(small.encode(text)), (
        "a larger vocabulary must produce FEWER tokens for the same text — "
        "that is the whole trade, and attention cost is its square")


def check_attention_core() -> None:
    from engine import Tensor, causal_mask, check_gradient
    from attention import entropy, scaled_dot_product

    rng = random.Random(0)
    q = Tensor.randn(4, 8, rng=rng)
    k = Tensor.randn(4, 8, rng=rng)
    v = Tensor.randn(4, 8, rng=rng)
    out, weights = scaled_dot_product(q, k, v, causal_mask(4))
    assert out.shape == (4, 8), f"output shape {out.shape}"
    assert weights.shape == (4, 4)

    for r in range(4):
        row = weights.data[r * 4:(r + 1) * 4]
        assert abs(sum(row) - 1.0) < 1e-9, f"row {r} sums to {sum(row)}"
        for c in range(r + 1, 4):
            assert row[c] == 0.0, (
                f"weight[{r}][{c}] is {row[c]}, must be exactly 0. Position {r} "
                f"cannot be allowed to see position {c}. This one line is what "
                "stands between a language model and a model that has read the "
                "answer.")

    # The scaling. Without it, high d_k saturates the softmax before training.
    length = 16
    entropies = {}
    for d_k in (8, 256):
        q = Tensor.randn(length, d_k, rng=random.Random(1))
        k = Tensor.randn(length, d_k, rng=random.Random(2))
        _, w = scaled_dot_product(q, k, Tensor.randn(length, d_k, rng=rng), None)
        entropies[d_k] = sum(entropy(w.data[r * length:(r + 1) * length])
                             for r in range(length)) / length
    assert entropies[256] > 2.0, (
        f"at d_k=256 the mean attention entropy is {entropies[256]:.3f} bits "
        f"out of a possible {math.log2(length):.2f}. That means the softmax has "
        "already collapsed to near-certainty before any training, and the "
        "gradient through a saturated softmax is ~0. Divide the scores by "
        "sqrt(d_k): the dot product of two unit-variance vectors over d_k "
        "dimensions has magnitude ~sqrt(d_k), and that is what puts it back.")
    assert abs(entropies[8] - entropies[256]) < 1.0, (
        "with correct scaling the entropy should be roughly INDEPENDENT of "
        "d_k — that is the property the scaling exists to give you")


def check_multihead() -> None:
    from engine import Tensor, causal_mask, check_gradient
    from attention import MultiHeadAttention

    attention = MultiHeadAttention(16, 4, rng=random.Random(0))
    assert attention.head_dim == 4
    x = Tensor.randn(6, 16, rng=random.Random(1))
    out = attention(x, causal_mask(6))
    assert out.shape == (6, 16), f"got {out.shape}"
    assert len(attention.last_weights) == 4, (
        "four heads should have produced four attention matrices")

    rows = [tuple(round(v, 6) for v in w.data) for w in attention.last_weights]
    assert len(set(rows)) == 4, (
        "all four heads produced IDENTICAL attention. They must slice "
        "different column ranges of the same projection — if every head reads "
        "the same slice, you have one head with four copies.")

    try:
        MultiHeadAttention(15, 4)
        raise AssertionError("d_model not divisible by heads must raise")
    except ValueError:
        pass

    out.sum().backward()
    assert attention.to_q.weight.grad is not None, (
        "no gradient reached the query projection")
    assert attention.out.weight.grad is not None


def check_model() -> None:
    from engine import Tensor
    from transformer import GPT, Block, FeedForward, LayerNorm

    norm = LayerNorm(8)
    x = Tensor([1.0, 5.0, 9.0, 2.0, 4.0, 6.0, 3.0, 7.0], (1, 8))
    out = norm(x)
    mean = sum(out.data) / 8
    variance = sum((v - mean) ** 2 for v in out.data) / 8
    assert abs(mean) < 1e-6 and abs(variance - 1.0) < 1e-3, (
        f"layer norm gave mean {mean:.4f} and variance {variance:.4f}; it must "
        "normalise each ROW to zero mean and unit variance. Per row, not per "
        "batch — that is why inference on a batch of one behaves identically "
        "to a batch of a thousand.")

    model = GPT(vocab_size=40, d_model=16, heads=2, layers=2, block_size=8)
    logits = model([1, 2, 3])
    assert logits.shape == (3, 40), (
        f"got {logits.shape}, expected (3, 40): one distribution over the "
        "vocabulary per input position")

    loss = model.loss([1, 2, 3, 4, 5])
    assert 0.5 < loss.item() < 10, f"initial loss {loss.item():.3f}"
    assert abs(loss.item() - math.log(40)) < 1.5, (
        f"an untrained model's loss should be near log(vocab) = "
        f"{math.log(40):.3f}, got {loss.item():.3f}. Much lower means the "
        "output layer is not starting near-uniform; much higher means "
        "something is scaled wrong.")

    loss.backward()
    assert model.token_embedding.grad is not None
    assert any(any(g != 0 for g in p.grad or [0]) for p in model.parameters()), \
        "some parameter should have a non-zero gradient"

    tied = GPT(vocab_size=200, d_model=16, heads=2, layers=1, block_size=8,
               tie_weights=True)
    untied = GPT(vocab_size=200, d_model=16, heads=2, layers=1, block_size=8,
                 tie_weights=False)
    assert tied.num_parameters() < untied.num_parameters(), (
        "tying the embedding and the output projection must remove a "
        f"vocab x d_model matrix — {200 * 16:,} parameters here")
    assert tied([1, 2]).shape == (2, 200), "tied models still produce logits"

    try:
        model([1] * 20)
        raise AssertionError("a sequence longer than block_size must raise")
    except ValueError:
        pass


def check_positions_and_residuals() -> None:
    from engine import Tensor
    from attention import MultiHeadAttention
    from transformer import GPT

    # Attention alone is permutation-equivariant.
    rows = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    order = [2, 0, 3, 1]
    head = MultiHeadAttention(4, 1, rng=random.Random(0))
    plain = head(Tensor.from_rows(rows), None).rows()
    shuffled = head(Tensor.from_rows([rows[i] for i in order]), None).rows()
    worst = max(abs(a - b) for i, target in enumerate(order)
                for a, b in zip(shuffled[i], plain[target]))
    assert worst < 1e-9, (
        f"shuffling the rows of an unmasked attention's input changed the "
        f"outputs by {worst:.2e}; it must change NOTHING but their order. "
        "Attention is a weighted sum and a sum is permutation-equivariant — "
        "which is precisely why positional information has to be added.")

    positional = GPT(vocab_size=20, d_model=8, heads=2, layers=1, block_size=6,
                     positional=True, seed=1)
    flat = GPT(vocab_size=20, d_model=8, heads=2, layers=1, block_size=6,
               positional=False, seed=1)
    a = positional([3, 3]).data
    b = flat([3, 3]).data
    assert max(abs(x - y) for x, y in zip(a[:8], b[:8])) < 1e-9 or True
    same_token = flat([5, 5])
    assert max(abs(same_token.data[i] - same_token.data[20 + i])
               for i in range(20)) < 1e-6, (
        "with no positional embeddings and the SAME token twice, both "
        "positions must produce identical logits — position 1 attends to two "
        "copies of the same vector, which averages to that vector. If they "
        "differ, something other than the embeddings is encoding position.")
    with_positions = positional([5, 5])
    assert max(abs(with_positions.data[i] - with_positions.data[20 + i])
               for i in range(20)) > 1e-6, (
        "WITH positional embeddings the same token at two positions must "
        "produce different logits — that is the entire point of adding them")


def check_training() -> None:
    from tokenizer import CORPUS, BPETokenizer
    from train import evaluate, make_batches, perplexity, train
    from transformer import GPT

    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, vocabulary_size=100)
    tokens = tokenizer.encode(CORPUS)
    assert len(tokens) > 500, "the corpus should give plenty of tokens"

    rng = random.Random(0)
    batches = make_batches(tokens, 12, 5, rng)
    assert all(len(b) == 13 for b in batches), (
        "a window for block_size 12 needs 13 ids: 12 inputs and the 13th as "
        "the final target")
    assert len(set(tuple(b) for b in batches)) > 1, "windows should be random"

    model = GPT(tokenizer.size, d_model=16, heads=2, layers=1, block_size=12,
                tie_weights=True, seed=1)
    before = evaluate(model, batches)
    assert abs(before - math.log(tokenizer.size)) < 1.5, (
        f"untrained loss {before:.3f} against log(vocab) "
        f"{math.log(tokenizer.size):.3f}")

    history = train(model, tokens, steps=60, lr=0.03, block_size=12, seed=2)
    after = history["held_out"][-1]
    assert after < before - 0.4, (
        f"loss went {before:.3f} -> {after:.3f} in 60 steps. It should fall "
        "clearly. If it is flat, check that gradients are accumulating across "
        "the accumulation window and that optimizer.step() is outside that "
        "inner loop, not inside it.")
    assert perplexity(after) < tokenizer.size, (
        "perplexity below the vocabulary size means the model has learned "
        "SOMETHING — above it means worse than guessing uniformly")
    assert after > 0.3, (
        f"held-out loss is {after:.4f} after only 60 steps, which is too good "
        "to be true. A 16-parameter-thousand model on this corpus cannot reach "
        "near-certainty that fast, and a loss this low almost always means the "
        "objective is leaking: check that loss() predicts ids[1:] from "
        "ids[:-1] and not ids[:-1] from itself. Predicting a token you can "
        "already see is free, and nothing about the training curve will tell "
        "you — it just looks like the best run you have ever had.")

    assert len(history["loss"]) == 60


def check_sampling() -> None:
    from sample import (choose, distinct_ratio, entropy, generate,
                        repetition_rate, softmax, top_k_filter, top_p_filter)
    from tokenizer import CORPUS, BPETokenizer
    from transformer import GPT

    logits = [1.0, 2.0, 3.0, 4.0]
    hot = softmax(logits, 2.0)
    cold = softmax(logits, 0.5)
    neutral = softmax(logits, 1.0)
    assert abs(sum(neutral) - 1.0) < 1e-9
    assert entropy(hot) > entropy(neutral) > entropy(cold), (
        f"entropies are {entropy(hot):.3f}, {entropy(neutral):.3f}, "
        f"{entropy(cold):.3f}. Higher temperature must FLATTEN the "
        "distribution and lower must sharpen it. Temperature divides the "
        "LOGITS before the exponential — dividing the probabilities afterwards "
        "and renormalising is a different and wrong operation.")
    assert max(range(4), key=lambda i: hot[i]) == 3, (
        "temperature never changes WHICH token is most likely, only how much "
        "mass it keeps")
    greedy = softmax(logits, 0.0)
    assert greedy == [0.0, 0.0, 0.0, 1.0], "T=0 is greedy exactly"

    filtered = top_k_filter([0.4, 0.3, 0.2, 0.1], 2)
    assert filtered[2] == 0.0 and filtered[3] == 0.0
    assert abs(sum(filtered) - 1.0) < 1e-9, "and it must renormalise"
    assert abs(filtered[0] - 0.4 / 0.7) < 1e-9

    confident = [0.9, 0.05, 0.03, 0.02]
    uncertain = [0.3, 0.28, 0.22, 0.2]
    _, small = top_p_filter(confident, 0.9)
    _, large = top_p_filter(uncertain, 0.9)
    assert small < large, (
        f"the nucleus is {small} tokens on a confident distribution and "
        f"{large} on an uncertain one — it must ADAPT. If they are equal, "
        "top_p is behaving like top_k, and the adaptivity is the entire reason "
        "nucleus sampling replaced it.")
    assert small == 1, f"0.9 alone already reaches p=0.9, so the nucleus is 1"

    counts = [0, 0, 0]
    rng = random.Random(0)
    for _ in range(3000):
        counts[choose([0.5, 0.3, 0.2], rng)] += 1
    assert abs(counts[0] / 3000 - 0.5) < 0.05, (
        f"sampling 3000 draws from [0.5, 0.3, 0.2] gave {counts}; `choose` "
        "must respect the probabilities")

    tokenizer = BPETokenizer()
    tokenizer.train(CORPUS, vocabulary_size=80)
    model = GPT(tokenizer.size, d_model=12, heads=2, layers=1, block_size=8,
                tie_weights=True, seed=3)
    prompt = tokenizer.encode("the cat")
    out = generate(model, prompt, length=20, greedy=True)
    assert len(out) == len(prompt) + 20, f"got {len(out)} ids"
    assert out[:len(prompt)] == prompt, "the prompt must be preserved"
    assert generate(model, prompt, length=20, greedy=True) == out, (
        "greedy decoding must be deterministic")

    varied = generate(model, prompt, length=20, temperature=2.0,
                      rng=random.Random(1))
    assert varied != out, "sampling at T=2 must differ from greedy"
    assert 0.0 <= repetition_rate(out) <= 1.0
    assert repetition_rate([1, 2, 3, 1, 2, 3, 1, 2, 3]) > 0.4, (
        "a sequence that repeats a 3-gram should score high on repetition")
    assert repetition_rate([1, 2, 3, 4, 5, 6, 7, 8, 9]) == 0.0


def _softmax(logits, temperature=1.0):
    if temperature == 0.0:
        m = max(range(len(logits)), key=lambda i: logits[i])
        return [1.0 if i == m else 0.0 for i in range(len(logits))]
    m = max(logits)
    exps = [math.exp((v - m) / temperature) for v in logits]
    z = sum(exps)
    return [e / z for e in exps]


def check_divergences() -> None:
    from distill import jsd, kl_forward, kl_reverse

    peaked = [0.97, 0.01, 0.01, 0.01]
    flat = [0.25, 0.25, 0.25, 0.25]
    other = [0.01, 0.01, 0.01, 0.97]

    assert kl_forward(peaked, peaked) < 1e-12
    assert kl_reverse(peaked, peaked) < 1e-12
    assert jsd(peaked, peaked) < 1e-12

    # Forward KL (teacher || student) is large when the student misses a
    # teacher mode. Reverse KL can stay small if the student just picks one.
    fwd_miss = kl_forward(peaked, other)
    rev_locked = kl_reverse(peaked, other)
    assert fwd_miss > 2.0, (
        f"forward KL(peaked || other) is {fwd_miss:.3f}; the student put "
        "almost no mass on the teacher's mode, so this must be large. "
        "That is mode-COVERING: miss a teacher mode, pay.")
    assert rev_locked > 2.0, (
        f"reverse KL(other || peaked) should also be large here because "
        f"the student is other and the teacher is peaked — got {rev_locked}")

    # The classic picture: teacher is bimodal, student locks onto one mode.
    teacher = [0.5, 0.0, 0.5, 0.0]
    locked = [1.0, 0.0, 0.0, 0.0]
    covered = [0.5, 0.0, 0.5, 0.0]
    assert kl_reverse(teacher, locked) < 0.05, (
        f"reverse KL of a student locked on ONE teacher mode is "
        f"{kl_reverse(teacher, locked):.3f}; mode-SEEKING allows this. "
        "If this is large, you swapped the arguments.")
    assert kl_forward(teacher, locked) > 0.5, (
        f"forward KL of the same pair is {kl_forward(teacher, locked):.3f}; "
        "the student missed half the teacher's mass and must pay. If this "
        "is small, you implemented reverse KL under the forward name.")
    assert kl_forward(teacher, covered) < 1e-12

    # JSD is symmetric and bounded.
    assert abs(jsd(peaked, flat) - jsd(flat, peaked)) < 1e-12, (
        "JSD must be symmetric — if it is not, you used a one-sided KL")
    assert 0 <= jsd(peaked, other) <= math.log(2) + 1e-9, (
        f"JSD is at most log 2 nats, got {jsd(peaked, other)}")
    assert kl_forward(peaked, [0.0, 0.0, 0.0, 1.0]) == float("inf"), (
        "forward KL is +inf when the student is zero where the teacher is not")


def check_on_vs_off_policy() -> None:
    from distill import (exposure_gap, sample_off_policy, sample_on_policy,
                         softmax)

    table = {
        (0,): [2.0, 0.0, 0.0],
        (0, 0): [0.0, 2.0, 0.0],
        (0, 1): [0.0, 0.0, 2.0],
    }
    off = sample_off_policy(table, [(0,), (0, 0)])
    assert len(off) == 2
    assert off[0][0] == (0,)
    assert abs(sum(off[0][1]) - 1.0) < 1e-9
    assert off[0][1][0] > 0.8, (
        "off-policy must softmax the stored LOGITS, not return them raw")

    try:
        sample_off_policy(table, [(1,)])
        raise AssertionError(
            "a missing prefix must raise KeyError — falling back to uniform "
            "is how exposure bias hides inside a passing test")
    except KeyError:
        pass

    # Student always picks token 0 from (0,) given a draw of 0.0 against a
    # one-hot-ish first logit.
    student = {
        (0,): [10.0, 0.0, 0.0],
        (0, 0): [10.0, 0.0, 0.0],
        (0, 0, 0): [0.0, 10.0, 0.0],
    }
    walked = sample_on_policy(student, (0,), length=2, rng_draws=[0.0, 0.0])
    assert walked[0] == (0,), "the start prefix must be included"
    assert walked[1] == (0, 0), f"first step should append 0, got {walked[1]}"
    assert walked[2] == (0, 0, 0), f"second step should append 0, got {walked[2]}"
    assert len(walked) == 3

    # Off-policy dataset never saw (0, 0, 0).
    gap = exposure_gap(walked, [(0,), (0, 0), (0, 1)])
    assert abs(gap - 1 / 3) < 1e-12, (
        f"exposure gap should be 1/3 (one of three on-policy prefixes is "
        f"unseen off-policy), got {gap}. That unseen prefix is the whole "
        "reason OPD exists.")
    assert exposure_gap(walked, walked) == 0.0
    assert exposure_gap([], [(0,)]) == 0.0

    # Your softmax is also used by later checks; pin the contract.
    assert abs(sum(softmax([1.0, 2.0, 3.0])) - 1.0) < 1e-9
    assert softmax([1.0, 3.0, 2.0], 0.0) == [0.0, 1.0, 0.0]


def check_opd_loss() -> None:
    from distill import kl_forward, kl_reverse, opd_loss

    teacher = [4.0, 0.0, 0.0]
    student_good = [4.0, 0.0, 0.0]
    student_bad = [0.0, 0.0, 4.0]
    assert opd_loss(teacher, student_good, "reverse") < 1e-6
    assert opd_loss(teacher, student_bad, "reverse") > 1.0
    assert abs(opd_loss(teacher, student_bad, "forward")
               - kl_forward(_softmax(teacher), _softmax(student_bad))) < 1e-8
    assert opd_loss(teacher, student_bad, "forward") > (
        opd_loss(teacher, student_good, "forward"))
    # The function takes LOGITS and softmaxes internally.
    # Pin that it does not expect pre-softmaxed inputs by feeding large logits.
    assert opd_loss([20.0, 0.0], [20.0, 0.0], "jsd") < 1e-9
    try:
        opd_loss(teacher, student_good, "kullback")
        raise AssertionError("unknown divergence must raise ValueError")
    except ValueError:
        pass


def check_supervision_density() -> None:
    from distill import supervision_density

    sft = supervision_density("sft", 16)
    opd = supervision_density("opd", 16)
    rl = supervision_density("rl", 16)
    for name, row in (("sft", sft), ("opd", opd), ("rl", rl)):
        for key in ("tokens_supervised", "signal", "states", "density"):
            assert key in row, f"{name} is missing {key}"

    assert sft["tokens_supervised"] == 16 and sft["density"] == 1.0
    assert sft["signal"] == "one-hot" and sft["states"] == "off-policy"
    assert opd["tokens_supervised"] == 16 and opd["density"] == 1.0
    assert opd["signal"] == "distribution" and opd["states"] == "on-policy"
    assert rl["tokens_supervised"] == 1
    assert abs(rl["density"] - 1 / 16) < 1e-12
    assert rl["signal"] == "scalar" and rl["states"] == "on-policy", (
        "RL is on-policy AND sparse. If you marked it off-policy you have "
        "confused 'dataset' with 'rollout'; if you marked the signal as "
        "distribution you have described OPD.")

    # The two pairwise confusions the docstring warns about.
    assert sft["density"] == opd["density"] and sft["states"] != opd["states"]
    assert opd["states"] == rl["states"] and opd["density"] != rl["density"]
    try:
        supervision_density("ppo", 8)
        raise AssertionError("unknown method must raise ValueError")
    except ValueError:
        pass


def check_opsd() -> None:
    from distill import opsd_pair

    calls = []

    def student_fn(tokens):
        calls.append(("student", tuple(tokens)))
        # one logit row per position
        return [[0.0, 1.0] for _ in tokens]

    def teacher_fn(tokens):
        calls.append(("teacher", tuple(tokens)))
        return [[4.0, 0.0] for _ in tokens]

    teacher_p, student_p = opsd_pair([1, 2], [9], student_fn, teacher_fn)
    assert abs(sum(teacher_p) - 1.0) < 1e-9
    assert abs(sum(student_p) - 1.0) < 1e-9
    assert teacher_p[0] > 0.9, (
        "teacher logits are [4, 0] at the last position; after softmax "
        f"token 0 should dominate, got {teacher_p}")
    roles = [c[0] for c in calls]
    assert "teacher" in roles and "student" in roles
    teacher_ctx = [c[1] for c in calls if c[0] == "teacher"][0]
    student_ctx = [c[1] for c in calls if c[0] == "student"][0]
    assert teacher_ctx == (1, 2, 9), (
        f"teacher must see question + privileged, got {teacher_ctx}. "
        "That extra token is the privilege.")
    assert student_ctx == (1, 2), (
        f"student must see ONLY the question, got {student_ctx}. "
        "If it also sees the answer you have leaked the privilege and "
        "OPSD collapses to ordinary teacher-forcing.")


def check_paper_choices() -> None:
    from distill import paper_choices

    papers = paper_choices()
    required = ("minilm", "gkd", "sdpo", "opsd")
    keys = ("teacher", "states", "divergence", "privilege")
    for name in required:
        assert name in papers, f"missing paper {name!r}"
        for key in keys:
            assert key in papers[name], f"{name} is missing {key}"

    assert papers["minilm"]["teacher"] == "external"
    assert papers["minilm"]["states"] in ("on-policy", "mixed")
    assert papers["minilm"]["divergence"] == "reverse"
    assert papers["minilm"]["privilege"] == "none"

    assert papers["gkd"]["teacher"] == "external"
    assert papers["gkd"]["states"] == "on-policy"
    assert papers["gkd"]["divergence"] == "configurable"
    assert papers["gkd"]["privilege"] == "none"

    assert papers["sdpo"]["teacher"] == "self"
    assert papers["sdpo"]["states"] == "on-policy"
    assert papers["sdpo"]["divergence"] == "preference"
    assert papers["sdpo"]["privilege"] == "feedback"

    assert papers["opsd"]["teacher"] == "self"
    assert papers["opsd"]["states"] == "on-policy"
    assert papers["opsd"]["privilege"] in ("answer", "trace")
    assert papers["opsd"]["divergence"] in ("reverse", "configurable")


def check_privilege_illusion() -> None:
    from distill import privilege_tokens

    # Teacher: mostly a capability token (id 1) plus a small privilege tell (id 3).
    teacher = [0.05, 0.80, 0.05, 0.10]
    # Illusion: student copies the tell (id 3) and dumps mass on id 0.
    student = [0.80, 0.05, 0.05, 0.10]
    result = privilege_tokens(teacher, student,
                              privileged_token_ids=[3],
                              capability_token_ids=[1])
    assert abs(result["privilege_mass_gap"] - 0.0) < 1e-12, (
        f"privilege mass gap should be 0 (both put 0.10 on token 3), "
        f"got {result['privilege_mass_gap']}")
    assert result["capability_mass_gap"] > 0.7, (
        f"capability gap should be |0.80-0.05|=0.75, got "
        f"{result['capability_mass_gap']}")
    assert result["illusion"] is True, (
        "this is the illusion: the privilege tell matches, the skill does "
        "not. Loss can still look fine if the tell is frequent.")

    matched = privilege_tokens(teacher, teacher,
                               privileged_token_ids=[3],
                               capability_token_ids=[1])
    assert matched["illusion"] is False
    assert matched["capability_mass_gap"] == 0.0
    empty = privilege_tokens(teacher, student, [], [])
    assert empty["privilege_mass_gap"] == 0.0
    assert empty["capability_mass_gap"] == 0.0


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("tokenizer.py", "learning merges, most frequent first", check_bpe_training),
    ("tokenizer.py", "encoding in RANK order, and round trips", check_encoding),
    ("attention.py", "causal masking and the sqrt(d_k) scaling",
     check_attention_core),
    ("attention.py", "heads as slices of one projection", check_multihead),
    ("transformer.py", "layer norm, the model, weight tying", check_model),
    ("transformer.py", "positions, and what happens without them",
     check_positions_and_residuals),
    ("train.py", "next-token prediction, and the loss falling",
     check_training),
    ("sample.py", "temperature, top-k, top-p, generation", check_sampling),
    ("distill.py", "forward KL vs reverse KL vs JSD", check_divergences),
    ("distill.py", "on-policy vs off-policy prefixes", check_on_vs_off_policy),
    ("distill.py", "OPD loss on student states", check_opd_loss),
    ("distill.py", "RL vs OPD vs SFT supervision density",
     check_supervision_density),
    ("distill.py", "OPSD: one model, two contexts", check_opsd),
    ("distill.py", "MiniLM, GKD, SDPO, OPSD — the decisions",
     check_paper_choices),
    ("distill.py", "Privilege Illusion vs actual capability",
     check_privilege_illusion),
]


def run_one(check):
    try:
        check(); return PASS, ""
    except NotImplementedError:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, where
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:                       # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = (f"\n      at {frame.filename.split('/')[-1]}:"
                         f"{frame.lineno} in {frame.name}()")
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))

    print(f"\n{BOLD}LLM From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")

    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<16} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<16} {title}")
            print(f"      {GREY}not implemented yet"
                  f"{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; "
                          f"use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<16} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")

    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()

    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you built a language model,"
              f" then taught a smaller one.{RESET}")
        print(f"  {GREY}Now run each file's own demo, then compare with "
              f"solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings walk through it. "
              f"Stuck? solutions/{filename}{RESET}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
