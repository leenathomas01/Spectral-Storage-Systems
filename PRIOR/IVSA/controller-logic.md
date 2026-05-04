# IVSA Controller Logic Specification

**Document:** SPEC/controller-logic.md  
**Version:** 1.0  
**Status:** Frozen (Pre-Physical Validation)

---

## 1. Overview

The IVSA controller transforms host data into spectral representations, manages substrate interaction, and performs recovery when coherence degrades. This document specifies the signal flow for all controller operations.

---

## 2. Write Path: Data → Spectral Excitation

### 2.1 Signal Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Host   │───▶│   LBA   │───▶│   FFT   │───▶│  Phase  │───▶│Substrate│
│  Data   │    │  Mapper │    │ Engine  │    │  Mod.   │    │  I/O    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
   4KB            Coord.        Spectrum      Torsion        Excite
   Block          Assign        Vector        Encode         Inject
```

### 2.2 Processing Steps

**Step 1: Ingestion**
- Input: Standard NVMe write command (4KB–64KB block)
- Action: Buffer data for spectral transformation

**Step 2: Spectral Mapping**
- Transform data to frequency domain via FFT
- Map to N orthogonal frequency bands (N = 1024, 2048, or 4096)
- Assign phase offsets based on torsional encoding scheme

**Step 3: Channel Assignment**
- **Legacy Channel (B₀):** High-amplitude, low-frequency patterns for block compatibility
- **Native Channel (Bₙ):** Phase-shifted patterns for high-order correlation/search

**Step 4: Excitation Generation**
- Synthesize multi-frequency excitation waveform
- Apply directional bias (torsional/chiral encoding)
- Normalize energy to prevent saturation

**Step 5: Substrate Injection**
- Pulse excitation into substrate
- **Critical:** This is ADDITIVE — no erase-before-write
- New pattern superimposes on existing interference field

**Step 6: Signature Storage**
- Compute baseline γ signature
- Store in controller metadata (overhead: <1% capacity)
- Used for subsequent read correlation

### 2.3 Write Path Constraints

| Constraint | Requirement |
|------------|-------------|
| Non-destructive | Write must not erase existing patterns |
| Additive | New data superimposes, does not overwrite |
| Bounded energy | Must not saturate substrate dynamic range |
| Signature capture | Baseline must be stored for recovery |

---

## 3. Read Path: Probe → Response Capture

### 3.1 Signal Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Host   │───▶│Signature│───▶│  Probe  │───▶│Substrate│───▶│  ADC    │
│  Read   │    │ Lookup  │    │  Gen.   │    │Response │    │ Capture │
│  Cmd    │    │         │    │         │    │         │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
   LBA           Baseline       Low-E        Resonant       Digital
   Request       Retrieve       Pulse        Envelope       Sample
```

### 3.2 Processing Steps

**Step 1: Command Reception**
- Input: Host read command with LBA
- Action: Map LBA to stored signature

**Step 2: Signature Retrieval**
- Fetch baseline signature from controller metadata
- This is the expected spectral pattern from write time

**Step 3: Probe Generation**
- Synthesize probe waveform matching baseline spectrum
- **Critical:** Probe energy < 1% of write energy
- This ensures non-destructive sensing

**Step 4: Substrate Probing**
- Inject low-energy probe into substrate
- Substrate responds with resonant modulation
- No state change occurs (non-destructive)

**Step 5: Response Capture**
- High-speed ADC samples resonant envelope
- Sampling rate matched to substrate bandwidth
- Output: Raw time-domain response vector

**Step 6: Filtering**
- Bandpass filter on orthogonal channels
- Noise rejection
- Output: Filtered response envelope

### 3.3 Read Path Constraints

| Constraint | Requirement |
|------------|-------------|
| Non-destructive | Probe must not alter substrate state |
| Low energy | Probe power < 1% write power |
| High-speed capture | ADC rate sufficient for bandwidth |
| Zero read-disturb | Δγ/read ≤ 0.001 over 10⁹ reads |

---

## 4. Reconstruction: Response → Data + γ Evaluation

### 4.1 Signal Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│   Raw   │───▶│  IFFT   │───▶│    γ    │───▶│ Branch  │───▶│  Host   │
│Response │    │ Engine  │    │  Calc   │    │ Logic   │    │  Data   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
   Envelope      Transform      Correlate     Route          Return
   Vector        to Freq.       w/Baseline    by Zone        Block
```

### 4.2 γ Computation

**Definition:**
```
γ = |⟨P, R⟩| / (‖P‖ · ‖R‖)
```

Where:
- P = probe/baseline signature (expected)
- R = substrate response (received)
- ⟨·,·⟩ = complex inner product (vdot)
- ‖·‖ = L2 norm

**Implementation:**
```python
def calculate_gamma(reference: np.ndarray, response: np.ndarray) -> float:
    """
    Compute correlation coherence between expected and received signals.
    
    Args:
        reference: Expected spectral signature (from write)
        response: Received resonant envelope (from read)
    
    Returns:
        γ value in range [0.0, 1.0]
    """
    correlation = np.vdot(response, reference)
    norm_ref = np.linalg.norm(reference)
    norm_resp = np.linalg.norm(response)
    
    if norm_ref == 0 or norm_resp == 0:
        return 0.0
    
    return np.abs(correlation) / (norm_ref * norm_resp)
```

### 4.3 Branching Logic

```
IF γ ≥ 0.9:
    → FAST PATH: Return data immediately
    → Latency: O(1), minimal cycles

ELSE IF 0.7 ≤ γ < 0.9:
    → RECOVERY PATH: Trigger Phase-Walk
    → Latency: 10-100x base (iterative)

ELSE IF 0.4 ≤ γ < 0.7:
    → STATISTICAL PATH: Cross-channel inference
    → Latency: 100-1000x base (approximate)

ELSE (γ < 0.4):
    → FAILURE: Unrecoverable
    → Action: Return error to host, flag for re-init
```

---

## 5. Recovery Engine: Coordinate Descent Phase-Walk

### 5.1 Algorithm Overview

When γ drops below the fast-path threshold, the controller executes iterative phase correction to realign the response with the expected signature.

**Core Insight:** The γ landscape is smooth and convex-ish. Local corrections accumulate to global recovery.

### 5.2 Algorithm: Coordinate-Wise Phase Correction

```python
def phase_walk_recovery(
    response: np.ndarray,
    baseline: np.ndarray,
    max_iterations: int = 15,
    gain: float = 0.5,
    target_gamma: float = 0.9
) -> Tuple[np.ndarray, float, int]:
    """
    Iteratively correct phase errors to maximize γ.
    
    Args:
        response: Current (degraded) response from substrate
        baseline: Expected signature from write time
        max_iterations: Maximum recovery cycles
        gain: Correction step size (0 < gain ≤ 1)
        target_gamma: Early termination threshold
    
    Returns:
        Tuple of (corrected_response, final_gamma, iterations_used)
    """
    current = response.copy()
    
    for iteration in range(max_iterations):
        gamma = calculate_gamma(baseline, current)
        
        # Early termination if target reached
        if gamma >= target_gamma:
            return current, gamma, iteration
        
        # Coordinate-wise phase correction
        for i in range(len(current)):
            if np.abs(current[i]) < 1e-10:
                continue  # Skip near-zero elements (erased)
            
            # Compute local phase error
            phase_error = np.angle(baseline[i]) - np.angle(current[i])
            
            # Apply damped correction
            correction = np.exp(1j * phase_error * gain)
            current[i] *= correction
    
    final_gamma = calculate_gamma(baseline, current)
    return current, final_gamma, max_iterations
```

### 5.3 Recovery Characteristics

| Property | Value | Notes |
|----------|-------|-------|
| Convergence | Monotonic | No oscillation in normal conditions |
| Typical iterations | 5-15 | To reach γ ≥ 0.7 |
| Gain parameter | 0.5 | Balances speed vs. stability |
| Parallelizable | Yes | Per-band corrections are independent |

### 5.4 Recovery Constraints

| Constraint | Requirement |
|------------|-------------|
| Monotonic convergence | γ must not decrease during walk |
| Bounded iterations | Hard limit prevents runaway |
| Deterministic | Same inputs produce same outputs |
| No substrate modification | Recovery is controller-only |

---

## 6. Latency Model

### 6.1 Path Latencies

| Path | Condition | Relative Latency | Absolute Estimate |
|------|-----------|------------------|-------------------|
| Fast | γ ≥ 0.9 | 1x | 1-10 μs |
| Recovery | 0.7 ≤ γ < 0.9 | 10-100x | 50-500 μs |
| Statistical | 0.4 ≤ γ < 0.7 | 100-1000x | 1-10 ms |
| Failure | γ < 0.4 | N/A | Error return |

### 6.2 Latency vs. Coherence Trade Curve

```
Latency
   │
   │                              ╱
   │                            ╱
   │                          ╱
   │                        ╱
   │                 ╱─────╱
   │          ╱─────╱
   │    ╱────╱
   │───╱
   └────────────────────────────────── γ
      0.4      0.7      0.9      1.0
       │        │        │
    Fail    Recover   Fast
```

**Key Insight:** Latency scales inversely with γ. Most reads (healthy substrate) hit the fast path. Recovery latency is the "insurance cost" for graceful degradation.

---

## 7. Host Interface Mapping

### 7.1 NVMe Command Translation

| NVMe Command | IVSA Operation |
|--------------|----------------|
| Write | Spectral synthesis + additive injection |
| Read | Probe + correlation + recovery (if needed) |
| Trim/Discard | Mark signature as reclaimable |
| Flush | Ensure metadata persistence |

### 7.2 SMART Attribute Mapping

| IVSA Metric | SMART Attribute | Interpretation |
|-------------|-----------------|----------------|
| Average γ | Media Wearout | Lower = more degraded |
| Recovery rate | Read Error Rate | Higher = more stress |
| Iteration count | ECC Corrections | Proxy for recovery cost |
| γ floor | Reallocated Sectors | Threshold warning |

---

## 8. Summary

The IVSA controller implements a complete signal-processing pipeline:

1. **Write:** Transform data to spectrum, inject as additive interference
2. **Read:** Low-energy probe, capture resonant response
3. **Evaluate:** Compute γ, route to appropriate path
4. **Recover:** Iterative phase correction when degraded
5. **Interface:** Present standard block device to host

**Controller dominance principle:** Reliability comes from DSP intelligence, not substrate perfection. The controller does more work so the substrate can be simpler.

---

## References

- See `architecture.md` for invariants and system model
- See `coherence-model.md` for detailed γ analysis
- See `mvs-constraints.md` for substrate requirements
