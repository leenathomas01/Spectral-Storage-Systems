# SSS Coherence Model

**Document:** SPEC/coherence-model.md  
**Version:** 0.1  
**Status:** Frozen — definition layer, not theory

---

## Purpose

This document defines the three metrics used in SSS and their relationships.
Nothing else.

If you misunderstand the measurement system, it is because you ignored this
file. Read it before reading anything else in SPEC/.

---

## 1. γ — Correlation Coherence (Reachability)

### Definition

```
γ(R, P) = |⟨R, P⟩| / (‖R‖ · ‖P‖)
```

Where:
- R ∈ ℂᴺ — received response vector (from probe)
- P ∈ ℂᴺ — reference pattern (stored at write time)
- ⟨·,·⟩ — complex inner product: ⟨R, P⟩ = Σᵢ Rᵢ · P̄ᵢ
- ‖·‖ — L2 norm

**Range:** γ ∈ [0, 1]

For N stored identities {P₁ … Pₙ}, we compute γᵢ = γ(R, Pᵢ) for all i.
This produces a correlation vector [γ₁, γ₂, ..., γₙ] used by H_E and correctness.

### What γ Measures

γ measures whether the system converged to *some* attractor basin.  
γ does not measure whether the correct basin was reached.  
γ does not measure whether basins are distinguishable from each other.

### ⚠️ Critical Warning

γ tends toward 1.0 in three distinct situations:

1. Valid memory — correct basin, unambiguous
2. Ambiguous memory — multiple basins equally reachable
3. Mis-selected memory — wrong basin, cleanly locked

In all three cases, γ ≈ 1.0.

**γ alone cannot distinguish these cases. Never use γ as the sole
validity metric.**

### Role in SSS

γ is a diagnostic for reachability. It is a necessary input to H_E and
correctness. It is not a sufficient condition for validity.

---

## 2. H_E — Identity Energy Entropy (Separation)

### Definition

Given N stored identities with correlation scores γ₁, γ₂, ..., γₙ
against a probe:

```
pᵢ = γᵢ² / Σⱼ γⱼ²

H_E = -Σᵢ pᵢ · ln(pᵢ)
```

**Normalization:** natural logarithm. H_E is measured in nats.  
**Distribution:** Σᵢ pᵢ = 1 by construction.

If Σⱼ γⱼ² ≈ 0 (no detectable correlation across any stored identity),
H_E is undefined. This corresponds to the noise floor regime (γ < 0.4
for all identities) and is treated as an invalid retrieval — not a
structural ambiguity failure.

### What H_E Measures

H_E measures the sharpness of the identity distribution over squared
correlations. It answers: are the stored identities distinguishable
from each other given this probe?

- H_E = 0 — distribution is a point mass on one identity (perfect separation)
- H_E = ln(N) — distribution is uniform (total ambiguity)
- H_E ≤ H_crit — identities are separable under current conditions

### Why Squared Correlations

Squaring γᵢ before normalizing makes H_E sensitive to energy concentration,
not just correlation amplitude. A system where one identity has γ = 0.9 and
all others have γ = 0.1 should look very different from one where all
identities have γ = 0.5. Squaring amplifies that difference.

H_amp (entropy over raw γᵢ, not squared) is retained for compatibility with
earlier prototype runs only. H_E is the operative metric.

### Threshold

```
H_crit = 1.0
```

H_crit is an empirical threshold, not a physical constant. Its value
depends on normalization (nats), N, and the codebook structure. 1.0 is
the current experimental value — the point where the identity distribution
ceases to be sharply peaked under these conditions.

Do not treat H_crit = 1.0 as universal.

### Role in SSS

H_E answers the structural validity question: are basins separated enough
to identify the target? It is independent of whether the correct basin was
selected (that is correctness, below).

---

## 3. correctness — Selection Accuracy

### Definition

```
predicted_id = argmax_i(γᵢ)
correctness  = (predicted_id == target_id)
```

If multiple identities share the maximum γᵢ, tie-breaking is
implementation-defined. Such cases typically correspond to high H_E
(structural ambiguity) and should be treated as invalid retrievals.

### What correctness Measures

correctness answers whether the basin the system selected matches the
target identity. It is a binary outcome per query.

### Role in SSS

correctness is the empirical check on selection. It can only be evaluated
when the target identity is known (i.e., in validation, not in deployment).

In deployment, correctness is not directly observable because target_id is
unknown. It is used only for validation and benchmarking. Do not treat it
as a runtime signal.

correctness depends primarily on SNR. At sufficiently low SNR, the system
selects the wrong basin with low H_E and high γ — a confident, clean,
wrong answer.

---

## 4. Decision Rule

A spectral memory retrieval is **valid** only when both conditions hold:

```
is_separable = (H_E ≤ H_crit)
is_correct   = (argmax_i(γᵢ) == target_id)

valid = is_separable AND is_correct
```

Convergence alone (γ → 1.0) is not sufficient.  
Separation alone (H_E ≤ H_crit) is not sufficient.  
Both are required.

---

## 5. Non-Equivalences

These are explicit. They are the most common sources of misinterpretation.

```
γ ≈ 1.0  ≠  valid memory
γ ≈ 1.0  ≠  correct identity selected
γ ≈ 1.0  ≠  identities are separable

H_E ≤ H_crit  ≠  correct identity selected
H_E ≤ H_crit  ≠  high γ

low H_E + high γ  ≠  valid
                     (mis-selection can produce exactly this)

correctness = TRUE  ≠  H_E ≤ H_crit
                        (correct selection can occur by chance inside a
                        structurally ambiguous field — do not infer
                        separability from a single correct outcome)
```

---

## 6. Metric Failure Cases

Concrete examples of how the metrics behave under failure. These are not
edge cases — they are the normal failure modes of the system.

### Case A — Structural Failure (Separation Failure)

```
γ        = 1.0    ← system converged cleanly
H_E      = 2.1    ← identity distribution is diffuse
valid    = FALSE  ← structural ambiguity
```

Cause: codebook coherence is insufficient for the identity density (ρ = N/D).
The probe landed in an overlapping region between basins.
Fix: increase α (Fourier energy fraction) or reduce N/D.
SNR improvement will not fix this.

### Case B — Dynamic Failure (Mis-Selection)

```
γ              = 1.0    ← system converged cleanly
H_E            = 0.0    ← distribution is sharply peaked
predicted_id   ≠ target ← peaked on the wrong identity
valid          = FALSE  ← mis-selection
```

Cause: SNR too low for reliable basin selection. The system found a clean,
sharp answer — the wrong one.
Fix: improve SNR.
Structural fixes (α, N/D) will not fix this.

### Case C — Partial Recovery (Potentially Valid)

```
γ              = 0.6    ← system partially converged
H_E            = 0.4    ← separable
predicted_id   = target ← correct basin
valid          = TRUE   ← meets decision rule, but low-confidence regime
```

The retrieval is valid by the decision rule. This represents a recoverable
state, not a stable high-fidelity read. γ < 0.9 indicates the system is
operating in the recovery zone — more iterations or a cleaner probe would
improve γ further. This is not a failure; it is degraded performance.

### Case D — Full Validity

```
γ              = 0.98   ← clean convergence
H_E            = 0.02   ← sharply peaked
predicted_id   = target ← correct
valid          = TRUE
```

All three metrics agree. This is the high-fidelity regime.

---

## 7. Metric Relationships

```
γ    →  input to H_E and correctness
H_E  →  function of all γᵢ, measures distribution shape
correctness  →  function of argmax(γᵢ) and ground truth
valid  →  function of H_E and correctness
```

γ is upstream. H_E and correctness are derived from it but measure
orthogonal properties. valid is the intersection of both.

These metrics form a minimal sufficient set for evaluating spectral memory
validity under the current model. No single metric is sufficient alone.

γ is directly observable from the probe response.
H_E and correctness are derived metrics computed from {γᵢ}.

---

## 8. What This Document Does Not Cover

- Why the metrics behave this way → `SPEC/attractor-model.md`
- The decision rule in operational context → `SPEC/phase-diagram.md`
- What has been empirically confirmed → `VALIDATION/STATUS.md`
- Physical substrate requirements → `HANDOFF/bench-protocol.md`
