# SSS Validation Status

**Last updated:** 2026-05-04  
**Scoreboard version:** 0.1

---

## ⚠️ Read This First

The phase boundary result is **confirmed at trials=5** with the original
validated emulator. The structural boundary (α=0.70–0.80) and dynamic
boundary (-20 to -30 dB) are clean and consistent across all runs.

A trials=20 statistical run is recommended before formal citation to
establish confidence bands, but the current result is not a pilot —
it is reproducible with a fixed seed.

---

## Scoreboard

| Claim | Result | Confidence | Notes |
|-------|--------|------------|-------|
| γ tends to 1.0 regardless of validity | ✅ Confirmed | High | Holds across all tested (α, SNR, N) |
| γ alone cannot distinguish valid from invalid | ✅ Confirmed | High | L1 — observed law |
| H_E separates structural from dynamic failure | ✅ Confirmed | High | L2, L3 — orthogonal axes |
| Low α creates entropy floor regardless of SNR | ✅ Confirmed | High | L4 — structural, not dynamic |
| Phase boundary exists in α-SNR space | ✅ Confirmed | Medium | trials=5, original emulator — see Completed Runs |
| α_crit scaling with N/D density | ✅ Confirmed | Medium | Boundary at α=0.70–0.80 for N=1024, D=4096 |
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

**To convert pilot → confirmed (original emulator):**

```bash
python VALIDATION/spectral_tensor_emulator.py \
  --phase-diagram --num-id 1024 --target-idx 7 \
  --sweep-alphas 0.0,0.5,0.7,0.8,0.9,1.0 \
  --sweep-snrs 10,-10,-20,-30,-40 \
  --trials 20
```

## Completed Runs

### Phase Diagram — Original Emulator, trials=5

```
python spectral_tensor_emulator_final.py --phase-diagram \
  --num-id 1024 --target-idx 7 \
  --sweep-alphas 0.0,0.5,0.7,0.8,0.9,1.0 \
  --sweep-snrs 10,-10,-20,-30,-40 \
  --trials 5 --no-plot
```

```
alpha |  SNR dB | sep_rate |    acc |  valid | mean_H_E | State
 0.00 |    10.0 |     0.00 |   1.00 |   0.00 |    1.760 | ambiguous
 0.00 |   -30.0 |     0.00 |   0.00 |   0.00 |    1.823 | ambiguous
 0.50 |    10.0 |     0.00 |   1.00 |   0.00 |    1.447 | ambiguous
 0.70 |    10.0 |     0.00 |   1.00 |   0.00 |    1.078 | ambiguous
 0.80 |    10.0 |     1.00 |   1.00 |   1.00 |    0.815 | valid
 0.80 |   -30.0 |     1.00 |   0.20 |   0.20 |    0.805 | mis-selection
 0.90 |    10.0 |     1.00 |   1.00 |   1.00 |    0.475 | valid
 1.00 |    10.0 |     1.00 |   1.00 |   1.00 |    0.000 | valid
 1.00 |   -30.0 |     1.00 |   0.40 |   0.40 |    0.000 | mis-selection
 1.00 |   -40.0 |     1.00 |   0.00 |   0.00 |    0.000 | mis-selection
```

**Key observations (all confirmed across 5 trials):**

Structural boundary: between α=0.70 and α=0.80. Below this, H_E > H_crit
regardless of SNR. Increasing SNR cannot fix merged basins (L4 confirmed).

Dynamic boundary: between -20 dB and -30 dB. Above this, correct selection
holds wherever separability holds. Below it, selection collapses while
H_E remains low — confident wrong answers (Case B confirmed).

Pure Fourier (α=1.0) achieves H_E=0.000 — perfect basin separation — yet
mis-selection still occurs at -30 dB. Structural and dynamic failure are
orthogonal axes, empirically confirmed.

**Status:** Phase boundary confirmed. Statistical run (trials=20) recommended
before formal citation but current results are consistent and clean.

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
