# IVSA Coherence Model Specification

**Document:** SPEC/coherence-model.md  
**Version:** 1.0  
**Status:** Frozen (Pre-Physical Validation)

---

## 1. Overview

In IVSA, the primary integrity metric is **Correlation Coherence (γ)**, which replaces Bit Error Rate (BER) as the fundamental measure of data integrity. This document specifies the mathematical definition, measurement methodology, and operational implications of γ.

---

## 2. Mathematical Definition

### 2.1 Correlation Coherence (γ)

**Definition:**

$$\gamma = \frac{|\langle R, P \rangle|}{\|R\| \cdot \|P\|}$$

Where:
- $R \in \mathbb{C}^N$ = received response vector (from substrate probe)
- $P \in \mathbb{C}^N$ = reference pattern (baseline signature from write)
- $\langle \cdot, \cdot \rangle$ = complex inner product: $\langle R, P \rangle = \sum_{i=1}^{N} R_i \cdot \overline{P_i}$
- $\|\cdot\|$ = L2 norm: $\|X\| = \sqrt{\sum_{i=1}^{N} |X_i|^2}$

**Properties:**
- Range: $\gamma \in [0, 1]$
- $\gamma = 1$: Perfect alignment (ideal reconstruction)
- $\gamma = 0$: Complete decorrelation (noise)
- Symmetric in magnitude: $\gamma(R, P) = \gamma(P, R)$

### 2.2 Relationship to Signal Theory

γ is equivalent to the **normalized cross-correlation** used in:
- Matched filtering (radar, communications)
- Template matching (signal processing)
- Channel estimation (OFDM systems)

This is not a novel metric — it's a well-understood signal processing primitive applied to storage.

### 2.3 Comparison to BER

| Aspect | BER | γ |
|--------|-----|---|
| Domain | Binary symbols | Complex vectors |
| Granularity | Per-bit | Per-pattern |
| Failure mode | Discrete errors | Continuous degradation |
| Recovery | ECC (parity reconstruction) | Phase optimization |
| Meaning | "How many bits flipped?" | "How aligned is the signal?" |

---

## 3. Integrity Zones

### 3.1 Zone Definitions

| Zone | γ Range | Functional Status | Reconstruction Mode | Latency Impact |
|------|---------|-------------------|---------------------|----------------|
| **High Fidelity** | 0.9 – 1.0 | Optimal | Deterministic (direct spectral match) | Minimal (O(1)) |
| **Coherence Drift** | 0.7 – 0.9 | Degraded | Iterative (phase retrieval loop) | Moderate (10-100x) |
| **Approximate Recovery** | 0.4 – 0.7 | Non-Linear | Statistical (cross-channel inference) | High (100-1000x) |
| **Spectral Noise** | < 0.4 | Unrecoverable | Re-initialization required | N/A (error) |

### 3.2 Zone Transition Behavior

```
γ = 1.0  ─────────────────────────────────────────────  Perfect
         │
         │  High Fidelity Zone
         │  • Direct reconstruction
         │  • No recovery needed
         │
γ = 0.9  ─────────────────────────────────────────────  Fast Path Threshold
         │
         │  Coherence Drift Zone
         │  • Phase-walk recovery triggered
         │  • 5-15 iterations typical
         │  • Monotonic convergence expected
         │
γ = 0.7  ─────────────────────────────────────────────  Recovery Threshold
         │
         │  Approximate Recovery Zone
         │  • Statistical inference required
         │  • Cross-channel redundancy exploited
         │  • Lower confidence, higher latency
         │
γ = 0.4  ─────────────────────────────────────────────  Noise Floor
         │
         │  Unrecoverable Zone
         │  • Signal buried in noise
         │  • Return error to host
         │
γ = 0.0  ─────────────────────────────────────────────  Pure Noise
```

### 3.3 Threshold Configurability

These thresholds are **controller parameters**, not physical constants:

```python
# Default thresholds (configurable)
GAMMA_FAST_PATH = 0.90      # Above: deterministic read
GAMMA_RECOVERY = 0.70       # Above: iterative recovery possible
GAMMA_APPROXIMATE = 0.40    # Above: statistical inference
# Below 0.40: unrecoverable
```

Different deployment scenarios may adjust these based on:
- Latency tolerance
- Reliability requirements
- Substrate characteristics

---

## 4. Degradation Model

### 4.1 Sources of γ Degradation

| Source | Effect on γ | Mechanism |
|--------|-------------|-----------|
| **Thermal noise** | Additive decrease | Random phase/amplitude perturbation |
| **Phase drift** | Multiplicative decrease | Systematic phase rotation |
| **Partial erasure** | Proportional decrease | Loss of spectral components |
| **Interference saturation** | Gradual decrease | Superposition limit reached |
| **Substrate aging** | Slow decrease | Material property changes |

### 4.2 Noise Model: Additive White Gaussian Noise (AWGN)

Under AWGN, the received signal is:

$$R = P + N$$

Where $N \sim \mathcal{CN}(0, \sigma^2 I)$ (complex Gaussian noise)

Expected γ under AWGN:

$$\mathbb{E}[\gamma] \approx \frac{\text{SNR}}{\text{SNR} + 1}$$

Where $\text{SNR} = \|P\|^2 / \sigma^2$

### 4.3 Phase Drift Model

Under uniform phase drift $\Delta\phi$:

$$R_i = P_i \cdot e^{j\Delta\phi_i}$$

Where $\Delta\phi_i \sim \mathcal{U}(-\theta, \theta)$ for drift strength $\theta$

Initial γ relationship:

$$\gamma_{\text{initial}} \approx |\text{sinc}(\theta)|$$

For small drift ($\theta < 0.5$ rad): $\gamma \approx 1 - \theta^2/6$

### 4.4 Partial Erasure Model

Under random erasure with probability $p$:

$$R_i = \begin{cases} P_i & \text{with probability } 1-p \\ 0 & \text{with probability } p \end{cases}$$

Expected γ:

$$\mathbb{E}[\gamma] \approx \sqrt{1-p}$$

For 25% erasure ($p = 0.25$): $\gamma_{\text{expected}} \approx 0.87$ (before additional noise)

---

## 5. Recovery Mechanisms

### 5.1 Spectral Redundancy

Data is encoded across multiple orthogonal frequency bands. If some bands are corrupted, the remaining bands provide reconstruction capability.

**Analogy:** Similar to OFDM subcarrier diversity in wireless communications.

**Implementation:**
- Encode same semantic information at multiple frequency offsets
- Recovery uses cross-band correlation to fill gaps
- Trade-off: Redundancy reduces effective density

### 5.2 Iterative Phase Retrieval (Phase-Walk)

When γ drops below 0.9, the controller attempts to recover by correcting phase errors.

**Algorithm:** Coordinate-wise descent on phase angles

```
FOR each iteration:
    FOR each frequency band i:
        Compute local phase error: Δφᵢ = angle(Pᵢ) - angle(Rᵢ)
        Apply correction: Rᵢ ← Rᵢ · exp(j · gain · Δφᵢ)
    Compute new γ
    IF γ ≥ target: RETURN success
RETURN partial_recovery
```

**Convergence properties:**
- Monotonic (γ increases each iteration, barring numerical noise)
- Bounded (fixed iteration limit)
- Deterministic (same inputs → same outputs)

### 5.3 Statistical Inference (Approximate Path)

When γ is between 0.4 and 0.7, exact reconstruction is unlikely. The controller uses statistical methods:

- **Belief propagation** across correlated bands
- **Maximum likelihood** estimation of original pattern
- **Confidence-weighted** output with error flags

This path trades accuracy for availability — suitable for applications tolerating approximate results.

---

## 6. Simulation Validation

### 6.1 Validated Properties (v0.4 Simulator)

| Property | Test Condition | Result |
|----------|----------------|--------|
| **Monotonicity** | γ vs. noise sweep | Confirmed — smooth decay, no cliffs |
| **Pull-in envelope** | Recovery at various drift levels | 1.2 rad recoverable to γ ≥ 0.67 |
| **Erasure tolerance** | 25% substrate nulled | γ ≈ 0.68 post-recovery |
| **Scaling** | N=200 writes, 4096 bands | No saturation, stable γ |
| **Convergence** | Phase-walk iterations | <15 passes to threshold |

### 6.2 Key Simulation Results

**γ vs. SNR Curve (v0.1):**
- Monotonic decay from γ ≈ 1.0 at high SNR to γ ≈ 0.1 at -5dB
- No discontinuities or chaotic regions
- Integrity zones clearly separated

**Recovery Curve (v0.3):**
- Initial γ (post-trauma): ~0.15
- Final γ (post-recovery): ~0.70
- Gain: >350%
- Iterations to threshold: <15

**Envelope Mapping (v0.4):**
- Drift range tested: 0.1 – 1.2 rad
- Writes tested: 50 – 200
- Bands tested: 1024 – 4096
- Result: Flat γ ≈ 0.67-0.69 across all conditions
- Conclusion: Architecture is over-robust for tested parameter ranges

---

## 7. Operational Implications

### 7.1 Health Monitoring

The controller continuously monitors γ to predict substrate health:

```python
def assess_health(gamma_history: List[float]) -> HealthStatus:
    """
    Assess substrate health from recent γ measurements.
    """
    avg_gamma = np.mean(gamma_history)
    trend = np.polyfit(range(len(gamma_history)), gamma_history, 1)[0]
    
    if avg_gamma >= 0.9 and trend >= -0.001:
        return HealthStatus.HEALTHY
    elif avg_gamma >= 0.7:
        return HealthStatus.DEGRADED
    elif avg_gamma >= 0.4:
        return HealthStatus.CRITICAL
    else:
        return HealthStatus.FAILED
```

### 7.2 Predictive Maintenance

γ trends enable predictive maintenance:

| Trend | Interpretation | Action |
|-------|----------------|--------|
| Stable high | Normal operation | None |
| Slow decline | Aging | Schedule replacement |
| Rapid decline | Acute damage | Immediate backup |
| Oscillating | Thermal instability | Check environment |

### 7.3 SMART Attribute Mapping

| γ-based Metric | SMART Attribute | Units |
|----------------|-----------------|-------|
| Average γ | Media Wearout Indicator | Percentage |
| γ floor | Reallocated Sector Count | Count (proxy) |
| Recovery frequency | Read Error Rate | Per 10⁶ reads |
| Avg. iterations | ECC Correction Count | Per read |

---

## 8. Comparison to Traditional ECC

### 8.1 ECC Approach (Traditional)

```
Data → Encode (add parity) → Store → Read → Decode (correct errors) → Data
```

- Assumes discrete symbol errors
- Correction capacity limited by code rate
- Failure is binary (correctable or not)

### 8.2 γ-Recovery Approach (IVSA)

```
Data → Transform → Superpose → Probe → Correlate → Optimize → Data
```

- Assumes continuous degradation
- Recovery is iterative optimization
- Failure is gradual (fidelity loss)

### 8.3 Trade-offs

| Aspect | ECC | γ-Recovery |
|--------|-----|------------|
| Overhead | Parity bits (~10-30%) | Controller compute |
| Latency | Fixed (decode time) | Variable (iteration count) |
| Failure mode | Cliff (exceed correction) | Graceful (resolution loss) |
| Parallelism | Limited | High (per-band) |

---

## 9. Summary

The coherence model provides:

1. **Single integrity metric (γ)** that captures all degradation modes
2. **Clear operational zones** with defined recovery paths
3. **Predictable degradation** — continuous, not catastrophic
4. **Controller-centric recovery** — DSP intelligence compensates for substrate imperfection
5. **Validated mathematics** — simulation confirms expected behavior

**Key insight:** Moving from "is each bit correct?" to "how aligned is the pattern?" fundamentally changes failure semantics from binary to analog, enabling graceful degradation.

---

## References

- See `architecture.md` for system invariants
- See `controller-logic.md` for recovery implementation
- See `../VALIDATION/simulator.py` for simulation code
