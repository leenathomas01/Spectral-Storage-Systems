# SSS Architectural Falsification Brief v1.0

**Document:** HANDOFF/falsification-brief.md  
**Status:** Mandatory Gate for Physical Validation  
**Purpose:** Define binary conditions for architectural validation or invalidation

---

## Preamble

This document defines explicit criteria under which the SSS architecture is:
- **Validated** — physical behavior matches theoretical predictions
- **Constrained** — behavior matches but with tighter bounds than expected
- **Invalidated** — fundamental assumptions proven false

**This document supersedes interpretation, intuition, and expectation.**

Results are evaluated strictly against the criteria below. There is no "partial pass."

---

## 1. Architectural Claims Under Test

The physical bench experiment tests the following structural claims:

| Claim | Statement | Test |
|-------|-----------|------|
| **C1: Distributed Identity** | Information is encoded non-locally across the substrate | 25% erasure should not annihilate signal |
| **C2: Non-Destructive Access** | Read operations do not alter stored state | Repeated reads should not decay γ |
| **C3: Gradient-Driven Recovery** | The γ landscape is smooth and optimizable | Phase-walk should converge monotonically |
| **C4: Controller Dominance** | Recovery capability comes from DSP, not substrate perfection | Damaged substrate should be recoverable via optimization |

---

## 2. Redlines — Architecture Invalidated

If ANY of the following conditions is observed, the SSS architecture is **invalidated** in its current form.

### R1: Non-Monotonic Recovery (Chaos)

**Trigger Condition:**  
γ oscillates, jumps, or reverses direction by > 0.05 between iterations during phase-walk recovery.

**What This Means:**  
The recovery landscape is chaotic, multi-basin, or otherwise not gradient-tractable. The simulator's smooth-basin assumption is false.

**Action:**  
STOP. Architecture requires fundamental redesign of recovery assumptions.

---

### R2: Read-Induced Decay (Destructive Access)

**Trigger Condition:**  
Repeated probe reads (≥100 cycles, no writes) reduce γ by > 0.001 per read.

**What This Means:**  
Physical access is destructive. The "non-destructive observer" invariant (I-4) is physically impossible for this substrate class.

**Action:**  
STOP. Architecture invalid without fundamental redesign of access semantics.

---

### R3: Envelope Collapse (Controller Failure)

**Trigger Condition:**  
Within simulated pull-in range (≤1.2 rad drift, ≤25% erasure), recovery fails to exceed γ = 0.7 after ≤15 iterations.

**What This Means:**  
Controller-side optimization cannot compensate for substrate degradation. The "controller dominance" assumption fails in physical reality.

**Action:**  
STOP. Architecture requires either:
- More powerful optimizer (architectural extension)
- Tighter substrate constraints (MVS revision)
- Fundamental rethinking of recovery model

---

### R4: Identity Annihilation (Locality)

**Trigger Condition:**  
≥25% physical erasure drives initial γ to approximately zero (< 0.1) with no detectable correlation.

**What This Means:**  
Information encoding is local, not distributed. The "holographic" core premise is false — damage erases data rather than degrading fidelity.

**Action:**  
STOP. Core architectural premise invalid.

---

## 3. Margins — Architecture Constrained

These outcomes do not invalidate the architecture but constrain feasible implementations.

### M1: Drift Overrun

**Condition:**  
Recovery succeeds but requires > 15 iterations or works only for drift < 1.2 rad.

**Effect:**  
Tightens MVS phase-stability bounds. May require:
- More stable substrate selection
- Environmental controls
- Higher recovery iteration budget

**Classification:** Constrain, not invalidate.

---

### M2: Density Saturation

**Condition:**  
Increasing write count (N > 200) reduces recoverable γ below 0.7 at low drift.

**Effect:**  
Limits achievable volumetric density. May require:
- Higher spectral resolution (more bands)
- Write energy normalization
- Reduced density targets

**Classification:** Constrain, not invalidate.

---

### M3: Noise Floor Sensitivity

**Condition:**  
Base γ < 0.4 at nominal conditions, but recovers via descent.

**Effect:**  
Raises probe SNR or redundancy requirements. May require:
- Higher probe energy (within non-destructive limit)
- Additional spectral redundancy
- Better noise shielding

**Classification:** Constrain, not invalidate.

---

### M4: Persistence Shortfall

**Condition:**  
Power-off drift exceeds expected bounds but remains recoverable.

**Effect:**  
Requires refresh mechanism or tighter environmental control.

**Classification:** Constrain, not invalidate (if recoverable).

---

## 4. Extensions — Allowed Only If Redlines Clear

Architectural extensions may be explored **only if no redline is violated**.

### Permitted Extensions

| Extension | Condition | Risk |
|-----------|-----------|------|
| Optimizer upgrade (momentum, SGD) | R1-R4 clear | Low |
| Redundancy scaling | R1-R4 clear | Low |
| Thermal compensation model | R1-R4 clear | Medium |
| Read caching (for marginal R2) | γ decay < 0.01/read | Medium |

### Disallowed Extensions

Any extension that:
- Masks destructive reads
- Collapses non-locality
- Introduces irreversible projection
- Violates invariants I-1 through I-8

---

## 5. Decision Matrix

| Outcome | Redlines | Margins | Decision |
|---------|----------|---------|----------|
| All clear | 0 triggered | Any | **GO** — Proceed to pilot |
| Margins only | 0 triggered | 1+ hit | **CONSTRAIN** — Update MVS, proceed |
| Single redline | 1 triggered | Any | **NO-GO** — Identify failure, revise |
| Multiple redlines | 2+ triggered | Any | **NO-GO** — Fundamental rethink |

---

## 6. Interpretation Discipline

When evaluating results:

- **No averaging away failures** — A single redline trip is disqualifying
- **No parameter re-tuning post-hoc** — Test with pre-declared parameters only
- **No narrative justification** — Data either matches criteria or doesn't
- **No performance arguments** — Topology matters, speed doesn't (at this stage)

---

## 7. Documentation Requirements

For any run, record:

1. **Pre-declared parameters** — Before run starts
2. **Raw γ traces** — Unprocessed measurements
3. **Redline checklist** — Binary pass/fail for each
4. **Margin assessment** — Which constraints affected
5. **Final verdict** — GO / NO-GO / CONSTRAIN

---

## 8. Summary

| Redline | Condition | Verdict if Triggered |
|---------|-----------|---------------------|
| R1 | γ non-monotonic (jumps > 0.05) | Architecture invalid |
| R2 | Read decay > 0.001/read | Architecture invalid |
| R3 | γ < 0.7 after 15 iterations | Architecture invalid |
| R4 | Initial γ ≈ 0 after 25% erasure | Architecture invalid |

**Any single redline = NO-GO**

This is the contract between theory and reality. If reality says no, we listen.

---

## References

- See `bench-protocol.md` for test procedures
- See `../SPEC/architecture.md` for invariant definitions
- See `../SPEC/mvs-constraints.md` for substrate requirements
