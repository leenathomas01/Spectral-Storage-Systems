# SSS Architecture Specification

**Document:** `SPEC/architecture.md`  
**Version:** `1.0`  
**Status:** `Frozen (Pre-Physical Validation)`

---

## 1. System Model

SSS treats storage as a signal recovery problem rather than a cell integrity
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
|                        SSS CONTROLLER                        |
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

These constraints define SSS. Violation of any invariant constitutes
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
