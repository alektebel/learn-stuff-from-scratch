"""
ToyLM — a stand-in language model. PROVIDED, NOT AN EXERCISE.

ContextCite attributes *a model's* response to *its* context. To study the
attribution method you need a model whose output genuinely depends on the
context — but not a large one, or the experiment stops being runnable.

ToyLM is a small, honest conditional language model:

    p(next word | context, query, generated so far)

It scores each vocabulary word by how often it appears in the context,
weighting each sentence of the context by its overlap with the query. So it
answers questions by drawing on the sentences that are actually relevant — and
if you delete the sentence holding the answer, the probability of that answer
collapses. That is exactly the signal ContextCite exploits.

It is a real probability model (normalised, deterministic, differentiable in
principle), not a lookup table. What it is not is a transformer: it has no
parameters to train and no notion of word order. That is a deliberate trade —
the ATTRIBUTION METHOD you implement is the paper's, applied to a model small
enough to run in pure Python. See the README for how to swap in a real
Hugging Face model once the method works.

Two properties matter for everything downstream, and both are guaranteed here:

  1. The vocabulary is FIXED at construction, from the full (unablated)
     context. Ablating a source must not change the vocabulary, or logits from
     different ablations would not be comparable.
  2. Scoring is deterministic. Same inputs, same logits, every time.
"""

import math
import re
from typing import Dict, List, Optional, Sequence

EOS = "<eos>"

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "this", "that", "these", "those", "it", "its", "their", "our", "we", "they",
    "what", "which", "who", "how", "did", "do", "does", "use", "used", "using",
}


def tokenize(text: str) -> List[str]:
    """Lowercase word tokens. Deliberately simple and dependency-free."""
    return re.findall(r"[a-z0-9]+", text.lower())


def content_words(text: str) -> List[str]:
    return [w for w in tokenize(text) if w not in _STOPWORDS]


def split_sentences(text: str) -> List[str]:
    """Split on sentence-ending punctuation or newlines."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


class ToyLM:
    """A context-grounded bag-of-words language model."""

    def __init__(self, context: str, query: str, context_weight: float = 40.0,
                 background_weight: float = 1.0, repeat_penalty: float = 0.05,
                 stopword_weight: float = 0.02, eos_base: float = 0.4,
                 temperature: float = 1.0):
        self.context_weight = context_weight
        self.background_weight = background_weight
        self.repeat_penalty = repeat_penalty
        self.stopword_weight = stopword_weight
        self.eos_base = eos_base
        self.temperature = temperature

        # Fixed vocabulary from the FULL context plus the query. Never recomputed.
        vocab = sorted(set(tokenize(context)) | set(tokenize(query)))
        self.vocab: List[str] = vocab + [EOS]
        self.index: Dict[str, int] = {w: i for i, w in enumerate(self.vocab)}
        self.query_terms = set(content_words(query))

    # -- scoring ------------------------------------------------------------

    def _sentence_relevance(self, sentence: str) -> float:
        """How much this sentence looks like an answer to the query."""
        words = set(content_words(sentence))
        if not self.query_terms:
            return 1.0
        return 1.0 + 3.0 * len(words & self.query_terms)

    def next_token_logits(self, context: str, generated: Sequence[str]) -> List[float]:
        """Unnormalised log-scores over the fixed vocabulary.

        `context` is the (possibly ablated) context string. Words from
        query-relevant sentences score highest; already-generated words are
        damped so generation does not repeat itself forever.
        """
        scores = [self.background_weight] * len(self.vocab)

        for sentence in split_sentences(context):
            relevance = self._sentence_relevance(sentence)
            for word in tokenize(sentence):
                slot = self.index.get(word)
                if slot is not None:
                    scores[slot] += self.context_weight * relevance

        for word, slot in self.index.items():       # content words carry the answer
            if word in _STOPWORDS:
                scores[slot] *= self.stopword_weight

        for word in generated:                      # discourage repetition
            slot = self.index.get(word)
            if slot is not None:
                scores[slot] *= self.repeat_penalty

        # End-of-sequence becomes likelier the longer the answer runs.
        scores[self.index[EOS]] = self.background_weight * (
            self.eos_base * (1.0 + len(generated)) ** 2)

        return [math.log(max(s, 1e-12)) / self.temperature for s in scores]

    def sequence_logits(self, context: str,
                        response: Sequence[str]) -> List[List[float]]:
        """Teacher-forced logits: one distribution per response token.

        Position t is scored given the true tokens before it, exactly as a
        causal LM would be evaluated. This is what ContextCite measures.
        """
        return [self.next_token_logits(context, response[:t])
                for t in range(len(response))]

    # -- generation ---------------------------------------------------------

    def generate(self, context: str, max_tokens: int = 12) -> List[str]:
        """Greedy decoding, stopping at EOS."""
        generated: List[str] = []
        for _ in range(max_tokens):
            logits = self.next_token_logits(context, generated)
            best = max(range(len(logits)), key=lambda i: logits[i])
            token = self.vocab[best]
            if token == EOS:
                break
            generated.append(token)
        return generated

    def __len__(self) -> int:
        return len(self.vocab)


# ---------------------------------------------------------------------------
# The running example, mirroring the one in the ContextCite README
# ---------------------------------------------------------------------------

CONTEXT = (
    "The dominant sequence transduction models are based on complex recurrent "
    "or convolutional neural networks. "
    "We propose a new simple network architecture, the Transformer, based "
    "solely on attention mechanisms. "
    "Experiments on two machine translation tasks show these models to be "
    "superior in quality while being more parallelizable. "
    "Our model achieves 28.4 BLEU on the WMT 2014 English-to-German "
    "translation task. "
    "The Transformer can reach a new state of the art in translation quality "
    "after being trained for twelve hours on eight P100 GPUs. "
    "Recurrent models typically factor computation along the symbol positions "
    "of the input and output sequences. "
    "We show that the Transformer generalizes well to other tasks such as "
    "English constituency parsing. "
    "Attention mechanisms allow modeling of dependencies without regard to "
    "their distance in the sequences."
)

QUERY = "What type of GPUs were used for training?"

# Index of the only sentence that names the GPU — the ground truth ContextCite
# should recover. Used by the checker and the evaluation.
GROUND_TRUTH_SOURCE = 4


def _demo() -> None:
    model = ToyLM(CONTEXT, QUERY)
    print(f"vocabulary: {len(model)} words (fixed, from the full context)")
    print(f"query: {QUERY!r}")

    response = model.generate(CONTEXT)
    print(f"\nresponse with the full context: {' '.join(response)}")

    sentences = split_sentences(CONTEXT)
    print(f"\ncontext has {len(sentences)} sentences; source "
          f"{GROUND_TRUTH_SOURCE} is the one that answers the query:")
    print(f"  [{GROUND_TRUTH_SOURCE}] {sentences[GROUND_TRUTH_SOURCE]}")

    without = " ".join(s for i, s in enumerate(sentences)
                       if i != GROUND_TRUTH_SOURCE)
    print(f"\nresponse WITHOUT that sentence: {' '.join(model.generate(without))}")
    print("\nThe answer depends on one source. ContextCite's job is to discover")
    print("that automatically, without being told which source it was.")


if __name__ == "__main__":
    _demo()
