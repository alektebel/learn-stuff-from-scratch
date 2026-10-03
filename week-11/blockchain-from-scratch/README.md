# Blockchain From Scratch — Bitcoin, then Ethereum

**SKELETON.** Files, signatures and the checker contract are in place. Nothing
is implemented and the checks are not written. See
[`../../TODO.md`](../../TODO.md) §8.

Pure Python 3 standard library. No network, no wallet, no coin.

## Why this directory exists

The repo already has two of the three answers to "what happens when machines
disagree":

| | [`raft/`](../../week-10/raft/) | [`dynamo-paper/`](../../week-10/dynamo-paper/) | **here** |
|---|---|---|---|
| faults tolerated | crash | crash | **Byzantine** — nodes that lie |
| membership | fixed, known | fixed, known | **open** — anyone joins |
| minority write | refused | accepted as a sibling | accepted, then possibly **erased** |
| the promise | one order, everywhere | eventual convergence | one order, *probably*, eventually |
| the cost | unavailable under partition | conflicts you must merge | electricity, or capital at risk |

That third column is the gap. Raft assumes participants follow the protocol and
that you know who they are; Dynamo assumes you would rather not agree at all.
Neither survives an open network where a participant profits by lying, and
Sybil resistance — proof of work or proof of stake — is the only new idea in
the whole subject.

Read it as distributed systems, not as finance. The interesting content is:
**what does it cost to make agreement expensive to rewrite, and what does that
buy you that a quorum cannot?**

## What you build

| File | Mechanism | Stubs |
|---|---|---|
| `chain.py` | Blocks, headers, Merkle trees, SPV proofs | 6 |
| `pow.py` | Proof of work, difficulty, retargeting | 5 |
| `utxo.py` | Unspent outputs, double spends, the mempool | 6 |
| `script.py` | A stack machine with no jumps, on purpose | 4 |
| `fork.py` | Reorgs, Nakamoto's `(q/p)^k`, selfish mining | 5 |
| `accounts.py` | Balances, nonces, and replay | 4 |
| `evm.py` | Gas, and halting bought with money | 6 |
| `trie.py` | Merkle-Patricia, and proving ABSENCE | 6 |
| `pos.py` | Casper FFG finality, slashing, accountable safety | 4 |

```bash
cd week-11/blockchain-from-scratch
python3 check.py          # 11 graded checks — NOT YET WRITTEN
```

## The four ideas worth the time

1. **Proof of work is a lottery, not a puzzle.** Finding a block is geometric
   with mean `2^difficulty` hashes. It buys exactly one thing: rewriting
   history costs the same again. Everything else people say about it is
   downstream of that sentence.
2. **Nakamoto's result is a probability, not a guarantee.** An attacker `k`
   blocks behind with hash share `q` catches up with probability `(q/p)^k`.
   "Six confirmations" is a risk tolerance someone picked. Simulate it against
   the closed form and you will never say "finalised" about a PoW chain again.
3. **Selfish mining says the incentives are not what the protocol assumes.**
   Withholding blocks earns more than your hash share above a threshold — and
   the threshold depends on how much of the honest network you can reach first.
   The protocol is safe; the *game* is not, and that distinction has no analogue
   in Raft.
4. **Proof of stake trades expensive for ATTRIBUTABLE.** PoW makes rewriting
   cost money. Casper FFG makes it produce *evidence*: two conflicting finalised
   checkpoints require at least a third of the stake to have signed contradictory
   attestations, and those signatures are the proof. `check_finality` builds the
   violation by hand and asserts it is caught — the same shape as Raft's
   Figure 8 check, for the same reason.

## Bitcoin vs Ethereum, as one design decision each

- **UTXO vs accounts.** A UTXO is spendable exactly once; that set *is* the
  double-spend defence. Accounts have balances, so nothing is consumed and a
  signed transaction stays valid forever — the nonce is the exact price of
  dropping the set. `accounts.py` runs the replay attack both ways.
- **No jumps vs gas.** Bitcoin Script has no loops, so every script provably
  halts and validation cost is bounded by length. Ethereum allows loops and
  therefore meets the halting problem, so it charges by the opcode and reverts
  when the money runs out. `evm.py` runs an infinite loop and terminates it.

## Where this stops

No real cryptography (`../../week-14/cryptographic-library/` has SHA-256; ECDSA
is not implemented here), no P2P networking, no wallet, no fee market beyond a
mempool selection rule, no light-client sync protocol, no zero-knowledge
anything, no bridges. It is the consensus and state-machine content, not a node.

## Sources

Full list, with what to read each for, in
[`../../REFERENCES.md`](../../REFERENCES.md#week-11--blockchain-from-scratch).
The four that carry this directory:

- Nakamoto, **"Bitcoin: A Peer-to-Peer Electronic Cash System"**, 2008 — §11 is
  the `(q/p)^k` that `fork.py` simulates against a closed form.
- Eyal & Sirer, **"Majority Is Not Enough"**, FC 2014 — selfish mining, and why
  the threshold depends on γ rather than being a single number.
- Lamport, Shostak & Pease, **"The Byzantine Generals Problem"**, TOPLAS 1982 —
  the fault model that separates this from `raft/`.
- Buterin & Griffith, **"Casper the Friendly Finality Gadget"**, 2017 —
  accountable safety and the ⅓ slashing bound `pos.py` checks.

Also: Wood's **Ethereum Yellow Paper** for the EVM, gas and the trie; Castro &
Liskov's **PBFT** (OSDI 1999) for BFT with *known* membership — the case Bitcoin
deliberately does not solve.

---

[← Week 5](../) · [Roadmap](../../ROADMAP.md) · [What remains](../../REMAINING.md)
