# SSS Engineering FAQ

**Document:** HANDOFF/engineering-faq.md  
**Audience:** Flash Controller and Reliability Engineers  
**Purpose:** Anticipate and address common technical objections

---

## Write Path Questions

### Q1: "How do you handle Write Amplification if there's no address?"

**Answer:**  
SSS eliminates classical Write Amplification because there's no "erase-before-write" cycle.

In NAND:
- Write → requires erased block
- Modify → requires read-erase-write cycle
- Garbage collection → amplifies writes

In SSS:
- Write = additive spectral injection
- New patterns superpose on existing field
- No block erasure, no garbage collection
- Effective WA during steady-state writes approaches 1.0

**Caveat:** There is a saturation limit (dynamic range). Once N patterns are superposed, further writes require substrate refresh. Periodic field refresh (compaction) introduces additional write cost, analogous to garbage collection in NAND. The difference is:
- Frequency is lower (depends on spectral capacity, not block invalidation)
- Scheduling is controllable (not triggered by fragmentation pressure)
- Cost is amortized across many writes rather than tied to each update

---

### Q2: "What happens when the interference field saturates?"

**Answer:**  
The substrate has finite dynamic range (ρ). As patterns accumulate:

1. **N < ρ threshold:** Full fidelity, γ ≈ 1.0
2. **N approaching limit:** γ begins to drop
3. **N at saturation:** New writes degrade old patterns

**Mitigation strategies:**
- Monitor cumulative write energy
- Proactive "compaction" (re-encode with fresh field)
- Higher spectral resolution (more orthogonal bands)

**Current spec:** ρ ≥ 20dB supports N ≈ 200 concurrent patterns per volume unit. Empirically observed scaling in simulation suggests sub-linear growth of capacity with spectral bands (approximately √bands under current conditions). This is not a proven law and depends on codebook structure and SNR.

---

## Read Path Questions

### Q3: "How is 'Non-Destructive Read' possible? You have to touch the state to see it."

**Answer:**  
We use **resonant/impedance sensing**, not charge extraction.

In NAND:
- Read = sample voltage on charge trap
- Charge leaks slightly each read
- Accumulates → read disturb

In SSS:
- Read = inject low-energy probe pulse
- Measure substrate's *response* (reflection/transmission)
- Substrate state unchanged (below modification threshold)

**Analogy:** Like radar — you detect the target by measuring echo, not by physically touching it.

**Energy budget:** Probe power < 1% of write power. This is the key constraint. If probe is too weak → noise. If too strong → disturb. There's a workable window (validated for LiNbO₃).

**Note:** "Non-destructive" means probe energy remains below the modification threshold of the substrate. Repeated reads may still introduce second-order effects (drift, heating), which must be validated experimentally.

---

### Q4: "What's the read latency if you need 15 iterations to recover?"

**Answer:**  
Latency is **conditional on substrate health**.

| Condition | Path | Iterations | Latency (est.) |
|-----------|------|------------|----------------|
| Healthy (γ ≥ 0.9) | Fast | 0 | 1-10 μs |
| Degraded (0.7 ≤ γ < 0.9) | Recovery | 5-15 | 50-500 μs |
| Stressed (0.4 ≤ γ < 0.7) | Statistical | 15+ | 1-10 ms |
| Failed (γ < 0.4) | Error | — | N/A |

**Key point:** For healthy storage (majority of reads), latency is competitive. Recovery latency is the "insurance premium" for graceful degradation.

**Comparison:** Similar to NAND soft-decision LDPC — most reads are fast, occasional retries when ECC is stressed.

---

### Q5: "Isn't the ECC overhead for 'signal recovery' massive?"

**Answer:**  
We don't use ECC in the traditional sense.

In NAND:
- Lose a bit → LDPC must reconstruct from parity
- Overhead: 10-30% for parity storage
- Failure: cliff when errors exceed correction capacity

In SSS:
- Lose spectral energy → correlate against remaining signal
- Overhead: controller compute (DSP), not storage
- Failure: graceful (fidelity loss, not data loss — measured via H_E, not γ alone)

**The trade:** We trade storage overhead (parity bits) for compute overhead (phase-walk iterations). With modern controllers having NPU/TPU blocks, compute is cheap and scales with Moore's Law. Storage overhead doesn't.

---

## Integrity Questions

### Q6: "If it's volumetric, how do you prevent inter-cell crosstalk?"

**Answer:**  
Crosstalk is a problem in **spatial** storage where adjacent cells interfere.

SSS uses **frequency-domain multiplexing**:
- Different data patterns occupy orthogonal spectral bands
- Overlap is intentional and controlled
- "Crosstalk" becomes "superposition" — a feature, not a bug

**Analogy:** OFDM in wireless. Thousands of users share the same spectrum via orthogonal subcarriers. We do the same with data patterns in a storage medium.

**The math:** Orthogonality is enforced by spectral encoding. Non-orthogonal components appear as noise, captured in γ.

---

### Q7: "What happens when the drive 'wears out'?"

**Answer:**  
NAND fails when oxide breaks → binary "bad block"

SSS fails when dynamic range narrows → analog degradation

| Stage | NAND | SSS |
|-------|------|------|
| Fresh | Full capacity | γ ≈ 1.0 |
| Aging | Growing bad block list | γ floor rises |
| End-of-life | Unusable sectors | γ < threshold |

**Key difference:** SSS degradation is continuous and predictable. You don't suddenly lose sectors — you gradually lose resolution. This enables:
- Better wear prediction
- Smoother end-of-life curve
- Potential for "graceful capacity reduction" instead of hard failure

---

## Controller Questions

### Q8: "Can a real controller handle this? What's the silicon cost?"

**Answer:**  
SSS controller requirements map to existing DSP primitives:

| SSS Function | Existing Block | Availability |
|---------------|----------------|--------------|
| Spectral transform | FFT engine | Common (5G basebands) |
| Phase correction | CORDIC / multiplier | Standard |
| Correlation | MAC array | Standard |
| Iterative loop | Microcontroller | Standard |

**Key insight:** We're not inventing new compute. We're repurposing signal-processing blocks that already exist in modern SoCs.

**Estimated overhead:** 10-20% additional controller die area vs. current NVMe controllers. Similar to the overhead added when going from SLC to QLC (more analog, more DSP).

---

### Q9: "Is the phase-walk convergent? What if it oscillates?"

**Answer:**  
This is one of our explicit kill-switches (R1: Chaos).

**Simulation results:** Across 10,000+ trials, phase-walk converges monotonically. No oscillations or divergence observed.

**Why it works:** Simulation indicates the γ surface is sufficiently smooth for coordinate descent to converge in tested regimes. This is an observed property, not a proven guarantee. High-density regimes may introduce local minima (see false coherence cases in `SPEC/coherence-model.md`).

**If physical testing shows oscillation:** Architecture is invalidated. We don't rationalize — we stop.

---

## Market Questions

### Q10: "Is 'graceful degradation' a sellable feature? Enterprise wants guarantees."

**Answer:**  
This is a genuine open question we'd like your input on.

**Arguments for:**
- AI workloads (model weights, embeddings) are noise-tolerant
- "90% confidence" may be acceptable for inference
- Predictable degradation enables capacity planning
- No surprise failures during critical operations

**Arguments against:**
- Enterprise IT culture expects binary reliability
- Compliance/audit may require hard guarantees
- "It probably works" is a hard sell

**Our position:** We're not claiming this replaces all storage. We're asking if there's a segment (AI inference, archival, approximate computing) where the trade-offs make sense.

---

## Physics Questions

### Q11: "Why Lithium Niobate? That's exotic."

**Answer:**  
LiNbO₃ is chosen as a **reference substrate** for physics validation, not as the production target.

**Why LiNbO₃:**
- Well-characterized photorefractive material
- Native volumetric interference (holographic storage heritage)
- Non-destructive read is proven
- Off-the-shelf availability

**Production candidates (future):**
- Phase-change materials (PCM derivatives)
- Ferroelectric domains
- Hybrid optical-electrical
- Novel materials TBD

**The architecture is substrate-agnostic.** LiNbO₃ lets us validate the controller/recovery math before committing to production material selection.

---

### Q12: "Your thermal assumptions seem optimistic. Real drives get hot."

**Answer:**  
Thermal sensitivity is captured in the "phase drift" parameter.

**Our model:**  
- Thermal expansion → phase shift
- Phase shift up to 1.2 rad → recoverable
- Beyond 1.2 rad → recovery fails

**Question for you:**  
What's the typical phase-equivalent drift in a real drive environment (40-70°C operating)? If it exceeds our envelope, we need to either:
- Tighten MVS constraints
- Add thermal compensation to controller
- Accept narrower operating range

**This is exactly the kind of reality check we're seeking.**

---

## Summary

**What we're confident about:**
- The math works (simulation validated)
- The signal-processing is standard (existing DSP primitives)
- The failure criteria are explicit (kill-switches defined)

**What we're uncertain about:**
- Physical substrate behavior (needs bench validation)
- Thermal coupling in real environments (needs expert input)
- Market acceptance of graceful degradation (needs business input)

**What we're asking:**
> "Tell us where we're wrong. We'd rather know now than after building hardware."

---

## The Engineering Hook

If you're still skeptical but intrigued, consider this framing:

> "Every generation of flash has added more analog complexity to solve digital physics problems — multi-level cells, soft-decision decoding, read-retry, etc. SSS just admits the substrate is fundamentally analog and applies Communication Theory instead of pretending it's digital. We're moving complexity from the medium (expensive, doesn't scale) to the controller (cheap, scales with Moore's Law)."

Whether that's brilliant or crazy — that's what we'd like your help determining.
