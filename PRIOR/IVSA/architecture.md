# IVSA Architecture Specification

**Document:** `SPEC/architecture.md`  
**Version:** `1.0`  
**Status:** `Frozen (Pre-Physical Validation)`

---

## 1. System Model

IVSA treats storage as a signal recovery problem rather than a cell integrity
problem.

### 1.1 Conceptual Model

```text
+----------------------+
|      HOST SYSTEM     |
| (NVMe / Block I/O)   |
+----------+-----------+
           |
           v
+---------------------------------------------------------------+
|                        IVSA CONTROLLER                        |
|                                                               |
|  Pattern Synthesis  |  Coherence Evaluator  | Recovery Engine |
|                     |       (gamma)         | (Phase / SIC)   |
+---------------------+-----------------------+-----------------+
           |
           v
+---------------------------------------------------------------+
|                    VOLUMETRIC SUBSTRATE                       |
|                                                               |
|  Distributed interference field (phase + frequency domain)    |
|                                                               |
|  - No discrete cells                                          |
|  - No fixed addresses                                         |
|  - Information exists in spectral relationships               |
+---------------------------------------------------------------+
```

### 1.2 Information Encoding

Information is not stored at locations. It is encoded as **spectral
constraints** superimposed onto a global interference field.

- **Write:** Add a new spectral pattern to the existing field.
- **Read:** Probe the field and correlate response against an expected signature.
- **Recovery:** Iteratively correct phase errors to maximize correlation.

---

## 2. Architectural Invariants

These constraints define IVSA. Violation of any invariant constitutes
non-conformance.

### 2.1 Universal Invariants (Must Hold)

| ID | Invariant | Description |
|----|-----------|-------------|
| I-1 | **Multiplexed Semantic Bases** | The substrate supports multiple simultaneous projections. No single interpretation is privileged. |
| I-2 | **Seed and Resonance Model** | At least one declared basis (`B0`) exists for backward compatibility. Additional bases may be discovered through interaction. |
| I-3 | **Projection Over Extraction** | All access occurs via projection and correlation, not point-to-point retrieval. |
| I-4 | **Non-Destructive Observer** | Read operations do not alter stored state. Probe energy is much smaller than write energy. |
| I-5 | **Phase Coherence Over Bit Integrity** | Preservation is defined by relational coherence (`gamma`), not symbol accuracy. |
| I-6 | **Identity as Cross-Basis Invariant** | Identity equals invariants preserved across all active projections. |
| I-7 | **Scale-Separated Orthogonality** | Different bases may coexist by operating at distinct structural scales. |
| I-8 | **One-Way Projection Boundary** | Classical interfaces interact only with reduced-dimensional projections. Latent structure remains inaccessible. |

### 2.2 Hard Prohibitions (Must Never Occur)

| ID | Prohibition | Consequence of Violation |
|----|-------------|-------------------------|
| P-1 | **No Atomic Ownership** | No basis may claim exclusive authority over any substrate region. |
| P-2 | **No Destructive Access** | Sequential, address-centric read and write is forbidden. |
| P-3 | **No Privileged Interpretation** | No basis is designated as "true" or "final." |
| P-4 | **No Null-Space Violation** | Adaptation may only occur in unclaimed degrees of freedom. |
| P-5 | **No Cross-Basis Collapse** | Operations in one basis must not degrade other bases. |

---

## 3. Controller Architecture

The controller mediates between host systems and the volumetric substrate.

### 3.1 Functional Blocks

```text
Host I/O
  |
  v
NVMe Frontend -> LBA-to-Spectrum Mapper -> Pattern Synthesis Module
                                              |
                                              v
                                        FFT / Transform Engine
                                              |
                                              v
Excitation Generator -> Substrate I/O -> Response ADC -> Coherence Evaluator
                                                      |
                                                      v
                                                Recovery Engine
                                              (Phase Walk / SIC)
```

### 3.2 Controller Responsibilities

| Function | Controller | Substrate |
|----------|------------|-----------|
| Encoding | Transforms data to spectral representation | Passively receives interference |
| Storage | Maintains signature metadata | Holds interference field |
| Integrity | Computes `gamma`, triggers recovery | Degrades predictably |
| Recovery | Executes controller-side optimization | Responds to probes |
| Interface | Presents block device semantics to host | None (no direct host access) |

**Design Principle:** Intelligence resides in the controller. The substrate is
deliberately "dumb" - it only needs to maintain a stable, predictable
interference field.

---

## 4. Integrity Model Summary

### 4.1 Primary Metric: Correlation Coherence (`gamma`)

```text
gamma = |<response, reference>| / (||response|| * ||reference||)
```

Where:

- `response` = substrate resonant response to probe
- `reference` = stored baseline signature from write time

**Range:** `0.0` (pure noise) to `1.0` (perfect correlation)

### 4.2 Integrity Zones

| Zone | Gamma Range | Status | Access Mode |
|------|-------------|--------|-------------|
| High Fidelity | `0.9 - 1.0` | Optimal | Deterministic (`O(1)`) |
| Coherence Drift | `0.7 - 0.9` | Degraded | Iterative Recovery |
| Approximate | `0.4 - 0.7` | Non-Linear | Statistical Inference |
| Noise Floor | `< 0.4` | Unrecoverable | Re-initialization Required |

### 4.3 Failure Semantics

- **Local damage -> global resolution loss** rather than localized data loss.
- **No single-point catastrophic failure** in the address-centric sense.
- **Graceful degradation** under noise, wear, or partial erasure.

### 4.4 Phase-Walk Capacity Constraint (Ideal-Simulator Result)

The current Version 1.0 recovery engine (`phase_walk_recovery`) shows a clear
capacity limit in the idealized validation model. To separate substrate loss
from controller quality, validation also uses **masked gamma**, which scores
only the non-erased bins after a `25%` erasure event.

**Validation context**

- Simulator only: no physical leakage, attenuation, or material decay beyond the binary erasure mask
- Substrate size: `4096` bands
- Recovery engine: coordinate-wise phase walk
- High-fidelity success criterion: masked `gamma >= 0.95`

| Concurrent Writes | Masked Gamma Median | Masked Gamma Range | High-Fidelity Success |
|-------------------|---------------------|--------------------|-----------------------|
| `1` | `~1.0000` | `0.99999999939 - 0.99999999972` | `20/20` |
| `2` | `0.8854` | `0.8810 - 0.8931` | `0/20` |
| `3` | `0.8516` | `0.8460 - 0.8585` | `0/20` |
| `4` | `0.8350` | `0.8302 - 0.8430` | `0/20` |
| `5` | `0.8260` | `0.8130 - 0.8366` | `0/20` |

**Interpretation**

- A single surviving pattern is recovered with effectively perfect masked coherence.
- The dominant failure mode is not substrate erasure; it is cross-pattern interference during recovery.
- The Version 1.0 phase-walk engine loses high-fidelity purity as soon as concurrent writes exceed `1`.
- Additional write density beyond `2` worsens coherence gradually, but the main collapse occurs at the transition from solo to multiplexed storage.

This is a **controller-side recovery constraint**, not a proof that IVSA itself
is low-capacity. Future recovery engines may raise this limit without changing
the architectural invariants.

---

## 5. Backward Compatibility

IVSA presents a standard block device interface to host systems.

### 5.1 External Interface

To external systems, IVSA appears as:

- Standard NVMe block device
- Optional key-value store
- Optional vector similarity store

### 5.2 Compatibility Guarantee

Legacy systems:

- Operate without awareness of volumetric encoding
- Cannot access or corrupt higher-order structure
- Observe only reduced-dimensional projection

This is enforced **structurally** through the one-way projection boundary, not
by firmware policy.

---

## 6. What This Architecture Does Not Specify

The following are explicitly deferred to implementation:

- Physical substrate material
- Optical versus electrical excitation
- Specific FFT and transform implementations
- Fabrication processes
- Performance targets
- Cost models

These are implementation choices, not architectural requirements.

---

## 7. Conformance Statement

Any system claiming IVSA conformance must:

1. Preserve all Universal Invariants (`I-1` through `I-8`)
2. Respect all Hard Prohibitions (`P-1` through `P-5`)
3. Use `gamma` (correlation coherence) as the primary integrity metric
4. Implement non-destructive read access
5. Support iterative recovery via controller-side optimization
6. Guarantee backward compatibility through structural projection

**Violation of any invariant constitutes non-conformance, regardless of
performance.**

---

## References

- See `controller-logic.md` for signal-flow specification
- See `coherence-model.md` for `gamma` computation and recovery mechanisms
- See `mvs-constraints.md` for substrate requirements
