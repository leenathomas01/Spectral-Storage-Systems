This repository is an open, falsifiable model. If it is wrong, it should fail under the conditions defined in VALIDATION/falsification-brief.md.

---

# Spectral Storage System (SSS)

**Status:** Mathematical validation in progress — physical bench pending  
**Version:** 0.1  
**Lineage:** See `PRIOR/`

---

## What This Is

SSS is a formal model for spectral memory — a system where identities are
stored as distributed interference patterns across a codebook of spectral bands,
and retrieved via correlation rather than address lookup.

It is not a product. It is not a claim about hardware. It is a minimal,
falsifiable mathematical model with a reproducible validation loop.

The simulator exists. The plots exist. The failure modes are explicit.
Physical implementation is a future question.

---

## The Core Insight (Why This Exists)

Traditional storage asks: *"Is this bit correct?"*

SSS asks: *"Is this identity reachable, separable, and correctly selected?"*

That shift from binary to structural produces three things:

- Potential for graceful degradation instead of catastrophic failure (observed in simulation; dependent on separation holding under physical noise — not yet physically validated)
- A richer validity signal than BER or ECC can provide
- A recovery model grounded in dynamical systems, not parity arithmetic

This model is relevant where:
- Data is naturally noisy or approximate (e.g., embeddings, inference weights)
- Storage systems already rely on probabilistic recovery (e.g., LDPC, soft decoding)

SSS explores whether these behaviors can be made first-class rather than corrective.

---

## The Two-Metric Problem

The central lesson from SSS development — hard-won across many iterations:

**γ (correlation coherence) is not a validity metric.**

γ measures reachability. A system can converge cleanly to γ ≈ 1.0 while
being wrong, ambiguous, or locked onto the wrong identity. This is not a
flaw to patch — it is a structural property of attractor-based systems.

Valid memory requires two independent conditions:

```
is_separable  = H_E <= H_crit        # identities are distinguishable
is_correct    = argmax(γᵢ) == target  # the right basin was selected
valid         = is_separable AND is_correct
```

Where:

- **H_E** (identity energy entropy) measures separation — are the basins
  distinct enough to tell apart?
- **correctness** measures selection — did the system land on the target?
- **γ** is retained as a reachability diagnostic, not a validity gate

This distinction — between *finding a state* and *knowing what state you
found* — is the conceptual spine of SSS.

---

## The Attractor Model

SSS treats stored identities as attractors in a structured spectral manifold.

- Each stored identity = an energy minimum in spectral correlation space
- Noise = a perturbation pushing the system away from that minimum
- Recovery = gradient descent back toward the attractor basin
- Phase-walk (the recovery algorithm) = an approximation of that descent

The graceful degradation zones follow directly from basin dynamics:

| Zone | γ Range | Dynamical Meaning |
|------|---------|-------------------|
| High Fidelity | > 0.9 | Deep inside basin — deterministic convergence |
| Coherence Drift | 0.7 – 0.9 | Near basin rim — iterative descent needed |
| Approximate | 0.4 – 0.7 | Between basins — probabilistic landing |
| Noise Floor | < 0.4 | No attractor in range — unrecoverable |

These zones are not heuristics. They are descriptions of dynamical behavior.

---

## Failure Modes

SSS distinguishes two structurally independent failure modes:

**Structural failure (separation failure)**
- Condition: `H_E > H_crit`
- Signature: γ ≈ 1.0, but identity entropy is high
- Cause: codebook coherence insufficient for density
- Fix: adjust α (Fourier energy fraction) or reduce ρ (N/D density)

**Dynamic failure (selection failure)**
- Condition: `argmax(γᵢ) ≠ target`
- Signature: γ ≈ 1.0, H_E ≤ H_crit, but wrong basin selected
- Cause: SNR too low for reliable selection
- Fix: improve SNR — structural fixes (α, ρ) cannot compensate

**Critical law:** Low α cannot be fixed by high SNR.  
Structural merging and dynamic confusion are orthogonal failure axes.

---

## Repository Structure

```
SSS/
├── README.md                        ← this file
│
├── SPEC/
│   ├── phase-diagram.md             ← frozen formal model + decision rule
│   ├── attractor-model.md           ← dynamical systems framing
│   └── coherence-model.md           ← γ, H_E, correctness definitions
│
├── VALIDATION/
│   ├── STATUS.md                    ← current validation scoreboard
│   ├── spectral_tensor_emulator.py  ← primary validation script
│   └── simulator.py                 ← prior envelope simulator (see PRIOR/)
│
├── HANDOFF/
│   ├── technical-memo.md            ← flash-engineer summary
│   ├── engineering-faq.md           ← anticipated objections
│   └── bench-protocol.md            ← physical validation protocol
│
└── PRIOR/
    └── IVSA/                        ← prior architecture specs (lineage)
```

---

## Current Validation State

See `VALIDATION/STATUS.md` for the full scoreboard.

Short version:

| Claim | Status |
|-------|--------|
| γ behaves as a reachability invariant in tested regimes | ✅ Confirmed — all tested regimes |
| H_E separates structural from dynamic failure | ✅ Confirmed |
| Phase boundary exists in α-SNR space | ⚠️ Observed (trials=1, not yet statistically confirmed) |
| Physical substrate behavior matches model | 🔲 Not yet tested |

The phase boundary is real in the pilot run. It is not yet a statistically
confirmed result. Do not treat it as one until `trials ≥ 20` is run.

---

## Running the Validator

```bash
# Capacity boundary sweep
python VALIDATION/spectral_tensor_emulator.py \
  --sweep-capacity \
  --sweep-alphas 0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0 \
  --sweep-ns 32,256,512,1024

# SNR sweep
python VALIDATION/spectral_tensor_emulator.py \
  --sweep-snr --num-id 1024 --target-idx 7 --codebook fourier

# Phase diagram (statistical — run this before citing boundary results)
python VALIDATION/spectral_tensor_emulator.py \
  --phase-diagram --num-id 1024 --target-idx 7 \
  --sweep-alphas 0.0,0.5,0.7,0.8,0.9,1.0 \
  --sweep-snrs 10,-10,-20,-30,-40 \
  --trials 20
```

---

## What This Is Not

- Not a product roadmap
- Not a claim about NAND replacement
- Not a physical storage device
- Not a validated hardware architecture

It is a mathematical model with a reproducible validation loop and explicit
falsification criteria. Physical implementation is a downstream question.

---

## Lineage

SSS evolved from a prior architecture (preserved in `PRIOR/`),
which itself grew from an earlier holographic storage concept (ZPRE-11).

The core pivot:

- The prior model used γ as the primary integrity metric
- SSS recognized γ is a reachability invariant only
- H_E and correctness were introduced as the true validity signals
- The physical substrate model (LiNbO₃ bench protocol) was preserved
  in HANDOFF/ for future implementation work

Full prior specification is in `PRIOR/` for lineage and reference.

---

## Contributors

Developed through collaborative exploration across multiple reasoning systems:  
Zee · Thea (ChatGPT) · Codex · Grok · Gemini · Muse Spark (Meta AI) . Claude .

*Architecture developed collaboratively. Falsification criteria declared in advance.*
