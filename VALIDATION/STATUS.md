# SSS Validation Status

**Last updated:** 2026-05-04  
**Scoreboard version:** 0.1

---

## ⚠️ Read This First

The phase boundary result is **observed, not confirmed.**

It was produced with `trials=1`. Until the statistical run (`trials ≥ 20`)
is complete, the phase diagram is a pilot result. It shows the right shape.
It is not a confidence-banded boundary.

Everything else in the table below is confirmed across multiple runs.

---

## Scoreboard

| Claim | Result | Confidence | Notes |
|-------|--------|------------|-------|
| γ tends to 1.0 regardless of validity | ✅ Confirmed | High | Holds across all tested (α, SNR, N) |
| γ alone cannot distinguish valid from invalid | ✅ Confirmed | High | L1 — observed law |
| H_E separates structural from dynamic failure | ✅ Confirmed | High | L2, L3 — orthogonal axes |
| Low α creates entropy floor regardless of SNR | ✅ Confirmed | High | L4 — structural, not dynamic |
| Phase boundary exists in α-SNR space | ⚠️ Observed | Low | trials=1 pilot only |
| α_crit scaling with N/D density | ⚠️ Observed | Low | See capacity surface plot |
| Physical substrate matches model | 🔲 Not tested | — | Bench protocol in HANDOFF/ |
| Recovery monotonicity on physical substrate | 🔲 Not tested | — | SSS R1 redline |
| Non-destructive read on physical substrate | 🔲 Not tested | — | SSS R2 redline |

---

## Current Validated Parameters

```
D = 4096 bands
N ∈ {32, 256, 512, 1024} identities
α ∈ [0.0, 1.0] Fourier energy fraction
H_crit = 1.0 (empirical, normalization-dependent)
Recovery mode: competitive elastic echo
```

---

## Observed Capacity Boundary

At `D=4096`, `SNR=-5 dB`, using true H_E:

| N | Observed α_crit |
|---|----------------|
| 32 | ≤ 0.00 |
| 256 | ≤ 0.00 |
| 512 | ≤ 0.30 |
| 1024 | ≤ 0.80 |

**Do not cite these as confirmed boundaries.** Run statistical validation first.

---

## Observed SNR Behavior

At `N=1024`, pure Fourier codebook:

| SNR Range | Result |
|-----------|--------|
| +30 dB to -20 dB | Correct lock, H_E = 0.000 |
| -30 dB and below | Wrong-basin lock, H_E = 0.000 |

Transition is sharp. H_E stays low in both cases — selection failure is
a confident wrong answer, not detectable from H_E alone.

---

## The Next Required Run

**To convert pilot → confirmed:**

```bash
python VALIDATION/spectral_tensor_emulator.py \
  --phase-diagram --num-id 1024 --target-idx 7 \
  --sweep-alphas 0.0,0.5,0.7,0.8,0.9,1.0 \
  --sweep-snrs 10,-10,-20,-30,-40 \
  --trials 20
```

Report should include:
- Mean P(valid) per (α, SNR) cell
- Standard deviation
- Separability rate vs. selection accuracy (separately)
- Stability of observed α_crit

Until this is run, the phase boundary is a hypothesis with supporting evidence.

---

## Physical Validation Gate

Before any physical implementation claim, the SSS redlines must clear:

| Redline | Condition | Status |
|---------|-----------|--------|
| R1: Chaos | γ oscillates during recovery (> 0.05 jump) | 🔲 Untested |
| R2: Decay | Reads degrade γ > 0.001/read | 🔲 Untested |
| R3: Collapse | γ < 0.7 after 15 iterations | 🔲 Untested |
| R4: Locality | 25% erasure → γ ≈ 0 | 🔲 Untested |

Any single redline failure = architecture invalidated in current form.

Full bench protocol: `HANDOFF/bench-protocol.md`
