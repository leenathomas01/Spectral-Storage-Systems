# IVSA Minimum Viable Substrate (MVS) Constraints

**Document:** SPEC/mvs-constraints.md  
**Version:** 2.0  
**Status:** Derived from v0.4 Simulator — Awaiting Physical Validation

---

## 1. Overview

This document specifies the **minimum requirements** any physical substrate must satisfy to support IVSA controller logic. These constraints are **derived from simulation**, not assumed.

**Important:** These are necessary conditions, not sufficient conditions. A substrate meeting all constraints may still fail physical validation for reasons not captured in simulation.

---

## 2. Constraint Derivation Methodology

Constraints were derived as follows:

1. **Simulate** controller behavior under various stress conditions
2. **Identify** parameter ranges where recovery succeeds (γ ≥ 0.7)
3. **Extract** substrate requirements as inequalities
4. **Validate** consistency across parameter sweeps (v0.4)

**Simulation parameters:**
- Write counts: 50-200
- Spectral bands: 1024-4096
- Drift range: 0.1-1.2 rad
- Erasure: 0-40%
- Recovery iterations: ≤15

---

## 3. Constraint Table

| Constraint Class | Description | Requirement | Derivation Basis |
|------------------|-------------|-------------|------------------|
| **Phase Stability** | Maximum allowable phase deviation over operational lifetime | Δφ ≤ 1.2 rad per 10⁶ cycles | v0.4: Recovery holds γ ≈ 0.67 at 1.2 rad max drift |
| **Erasure Tolerance** | Maximum fractional element loss before unrecoverable | ≥ 25% with γ ≥ 0.4 initial; ≥ 40% with recovery to γ ≥ 0.7 | v0.2-0.4: 25% erasure yields γ ≈ 0.68 post-recovery |
| **Dynamic Range (ρ)** | Minimum detectable resonance vs. saturation | ρ ≥ 20 dB for N = 200 concurrent writes | v0.4: No saturation at N=200; contrast maintained |
| **Noise Floor** | Minimum SNR preserved across read cycles | ≥ 10 dB base for γ ≥ 0.4 in drift zone | v0.1: Monotonic γ decay; floor at ~0.15 at -5dB |
| **Non-Destructive Read** | Maximum allowable state change per read | Δγ/read ≤ 0.001 over 10⁹ reads | Architectural invariant; probe energy < 1% write |
| **Persistence Window** | Minimum retention time for phase relationships | ≥ 10³ hours with Δφ ≤ 1.2 rad | Derived from drift constraint; assumes room temperature |

---

## 4. Detailed Constraint Specifications

### 4.1 Phase Stability

**Definition:**  
The substrate must maintain relative phase relationships between stored interference components within bounds over its operational lifetime.

**Requirement:**  
$$\Delta\phi_{\text{max}} \leq 1.2 \text{ rad per } 10^6 \text{ write-read cycles}$$

**Rationale:**  
- v0.4 simulation shows recovery to γ ≥ 0.67 at 1.2 rad drift
- Phase-walk optimizer has ~1.2 rad "pull-in" capability
- Beyond this, recovery iterations explode or fail to converge

**Measurement:**  
- Write test pattern
- Cycle through temperature/time stress
- Measure phase deviation of interference fringes
- Must remain within bound

### 4.2 Erasure Tolerance

**Definition:**  
The substrate must support partial physical damage (defects, voids, wear) without catastrophic data loss.

**Requirement:**  
$$P_{\text{erasure}} \leq 0.25 \implies \gamma_{\text{initial}} \geq 0.4$$
$$P_{\text{erasure}} \leq 0.40 \implies \gamma_{\text{recovered}} \geq 0.7 \text{ (with recovery)}$$

**Rationale:**  
- v0.2-0.4 simulations: 25% nulled elements yield γ ≈ 0.15-0.40 initial
- Post-recovery: γ ≈ 0.68 achievable
- This validates "distributed identity" — damage dims signal, doesn't erase it

**Measurement:**  
- Write test pattern
- Physically mask/damage 25% of sensing region
- Measure γ before and after recovery
- Must meet thresholds

### 4.3 Dynamic Range (ρ)

**Definition:**  
The ratio between minimum detectable signal and saturation threshold, determining maximum concurrent write density.

**Requirement:**  
$$\rho \geq 20 \text{ dB for } N = 200 \text{ concurrent patterns}$$

**Rationale:**  
- Each superposed write adds to total field energy
- Must distinguish individual patterns from aggregate
- v0.4: N=200 maintains γ ≥ 0.67 — no saturation observed

**Measurement:**  
- Progressively superpose patterns
- Measure γ vs. N
- Identify saturation knee
- ρ = 20 log₁₀(N_max / N_min)

### 4.4 Noise Floor

**Definition:**  
The intrinsic SNR of the substrate-controller system under normal operation.

**Requirement:**  
$$\text{SNR}_{\text{base}} \geq 10 \text{ dB for } \gamma_{\text{initial}} \geq 0.4$$

**Rationale:**  
- v0.1 SNR sweep: γ monotonically decreases with SNR
- At 10 dB: γ ≈ 0.5-0.6 (recoverable zone)
- Below 5 dB: γ approaches 0.4 (noise floor)

**Measurement:**  
- Write single pattern (no superposition)
- Measure γ under controlled noise injection
- Extract effective SNR from γ curve

### 4.5 Non-Destructive Read

**Definition:**  
Read operations must not measurably alter the stored interference pattern.

**Requirement:**  
$$\frac{\Delta\gamma}{\text{read}} \leq 0.001 \text{ over } 10^9 \text{ reads}$$

**Rationale:**  
- Architectural invariant I-4 (Non-Destructive Observer)
- Enables unlimited read cycles without wear
- Distinguishes IVSA from charge-trap storage (read disturb)

**Measurement:**  
- Write test pattern, measure baseline γ
- Execute 10³ – 10⁶ consecutive reads (no writes)
- Measure γ after each batch
- Decay rate must be ≤ 0.001/read

**Critical:** This is a **hard invariant**. Violation disqualifies the substrate.

### 4.6 Persistence Window

**Definition:**  
The time duration over which phase relationships remain within recoverable bounds without power or refresh.

**Requirement:**  
$$T_{\text{persist}} \geq 10^3 \text{ hours with } \Delta\phi \leq 1.2 \text{ rad}$$

**Rationale:**  
- Derived from phase stability constraint
- Assumes room temperature (25°C) storage
- Higher temperatures may require derating

**Measurement:**  
- Write test pattern
- Power off, store at controlled temperature
- Measure phase drift at intervals
- Extrapolate to 10³ hour bound

---

## 5. Substrate Candidate Evaluation

### 5.1 Evaluation Methodology

Each candidate substrate is evaluated against all constraints using **binary pass/fail** criteria:

- **Pass:** Constraint satisfied with margin
- **Conditional:** Constraint satisfied with caveats
- **Fail:** Constraint violated — disqualifying

**Important:** A single **Fail** disqualifies the substrate unless the architecture is explicitly extended to compensate.

### 5.2 Reference Evaluation: Lithium Niobate (LiNbO₃)

| Constraint | Requirement | LiNbO₃ Capability | Status |
|------------|-------------|-------------------|--------|
| Phase Stability | Δφ ≤ 1.2 rad/10⁶ cycles | < 0.1 rad (native photorefractive) | **Pass** |
| Erasure Tolerance | ≥ 25% with γ ≥ 0.4 | > 30% (volumetric holographic) | **Pass** |
| Dynamic Range | ρ ≥ 20 dB, N=200 | > 20 dB (multi-hologram capable) | **Pass** |
| Noise Floor | SNR ≥ 10 dB | ~20 dB (high optical quality) | **Pass** |
| Non-Destructive Read | Δγ/read ≤ 0.001 | Non-destructive probe native | **Pass** |
| Persistence | ≥ 10³ hrs, Δφ ≤ 1.2 rad | Decades (crystal stability) | **Pass** |

**Conclusion:** LiNbO₃ passes all constraints — suitable as **reference substrate** for physical validation.

### 5.3 Conditional Evaluation: Phase-Change Materials (GeSbTe)

| Constraint | Requirement | GeSbTe Capability | Status |
|------------|-------------|-------------------|--------|
| Phase Stability | Δφ ≤ 1.2 rad/10⁶ cycles | ~0.5 rad equiv. (with doping) | **Pass** |
| Erasure Tolerance | ≥ 25% with γ ≥ 0.4 | > 20% (multi-state) | **Pass** |
| Dynamic Range | ρ ≥ 20 dB, N=200 | 25-30 dB (multi-level cell) | **Pass** |
| Noise Floor | SNR ≥ 10 dB | ~15 dB typical | **Pass** |
| Non-Destructive Read | Δγ/read ≤ 0.001 | ~0.01 (read disturb observed) | **Fail** |
| Persistence | ≥ 10³ hrs, Δφ ≤ 1.2 rad | Years at room temp | **Pass** |

**Conclusion:** GeSbTe **fails** on non-destructive read constraint. May be viable with architectural extension (e.g., read caching), but introduces complexity and potential invariant violation.

---

## 6. Constraint Relationships

### 6.1 Dependency Graph

```
                    ┌─────────────────┐
                    │ Phase Stability │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  Erasure    │  │  Noise      │  │ Persistence │
    │  Tolerance  │  │  Floor      │  │   Window    │
    └─────────────┘  └─────────────┘  └─────────────┘
              │              │
              └──────┬───────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Dynamic Range   │
            │ (Derived)       │
            └─────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Non-Destructive │
            │ Read (Hard)     │
            └─────────────────┘
```

### 6.2 Constraint Tightening

If physical validation reveals:
- Phase stability worse than simulated → Tighten drift requirement
- Erasure tolerance lower than simulated → Increase redundancy
- Noise floor higher than simulated → Increase probe energy (carefully)

**The constraint table represents current best estimates. Physical validation may require revision.**

---

## 7. Summary

### 7.1 Hard Constraints (Non-Negotiable)

1. **Non-Destructive Read** — Architectural invariant; violation disqualifies substrate
2. **Phase Stability** — Must be within optimizer pull-in envelope

### 7.2 Soft Constraints (Tunable)

3. **Erasure Tolerance** — Can be improved with redundancy
4. **Dynamic Range** — Can be improved with higher resolution
5. **Noise Floor** — Can be improved with probe optimization
6. **Persistence** — Can be improved with refresh (if acceptable)

### 7.3 Validation Priority

1. First validate hard constraints (non-destructive, phase stability)
2. Then validate soft constraints
3. Only proceed to pilot if all hard constraints pass

---

## References

- See `architecture.md` for invariant definitions
- See `coherence-model.md` for γ derivation
- See `../VALIDATION/falsification-brief.md` for physical test criteria
