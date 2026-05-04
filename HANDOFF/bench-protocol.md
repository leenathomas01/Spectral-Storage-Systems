# SSS Bench Protocol v1.0

**Document:** HANDOFF/bench-protocol.md  
**Status:** Ready for Physical Execution  
**Reference Substrate:** Lithium Niobate (LiNbO₃)

---

## 1. Objective

Validate that physical substrate behavior matches simulator predictions.

**This is a topology validation, not a performance demo.**

We are testing whether:
1. γ behaves monotonically under stress
2. Recovery converges as predicted
3. Reads are non-destructive
4. Identity persists under partial damage

This setup is a reference validation rig, not an optimized or production-grade system.

---

## 2. Equipment (Bill of Materials)

### 2.1 Core Components

| Component | Specification | Purpose | Est. Cost |
|-----------|--------------|---------|-----------|
| LiNbO₃ Crystal | 5×5 cm, photorefractive doped | Reference substrate | ~$400 |
| Laser Diode | 532nm, 50mW, coherent | Write/probe excitation | ~$250 |
| SLM | LCOS 1024×768 | Phase spectrum synthesis | ~$800 |
| CCD Sensor | 1024×1024, monochrome | Resonant envelope capture | ~$900 |
| FPGA Board | Xilinx Zynq-7000 | Controller logic | ~$300 |
| Beam Optics | Splitter, lenses, mirrors | Optical path | ~$400 |
| Power/Misc | PSU, mounts, cables | Infrastructure | ~$200 |

**Total Estimated Cost:** ~$3,250

### 2.2 Optional Components

| Component | Purpose |
|-----------|---------|
| Temperature controller | Drift injection |
| Oscilloscope | Signal debugging |
| Optical power meter | Energy calibration |

---

## 3. Rig Assembly

### 3.1 Optical Path

```
                    ┌─────────────┐
                    │   LASER     │
                    │  (532nm)    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   BEAM      │
                    │  SPLITTER   │
                    └──────┬──────┘
                     ╱           ╲
                    ╱             ╲
                   ▼               ▼
          ┌─────────────┐   ┌─────────────┐
          │  REFERENCE  │   │    SLM      │
          │    BEAM     │   │  (Object)   │
          └──────┬──────┘   └──────┬──────┘
                 │                 │
                 └────────┬────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   LiNbO₃    │
                   │  CRYSTAL    │
                   └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    CCD      │
                   │  SENSOR     │
                   └─────────────┘
```

### 3.2 Control Path

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│   HOST   │────▶│   FPGA   │────▶│  LASER   │
│   PC     │     │  Zynq    │     │  DRIVER  │
└──────────┘     └────┬─────┘     └──────────┘
                      │
                      ├──────────▶ SLM Control
                      │
                      └──────────▶ CCD Capture
```

### 3.3 Assembly Steps

1. Mount LiNbO₃ crystal on optical table (vibration isolated)
2. Align laser to crystal center
3. Position beam splitter at 45°
4. Connect SLM to FPGA GPIO
5. Position CCD to capture interference pattern
6. Wire FPGA ADC input from CCD
7. Load controller firmware (FFT + descent algorithm)
8. Calibrate optical alignment (target: baseline γ = 1.0 ± 0.02)

---

## 4. Pre-Run Calibration

### 4.1 Optical Alignment Check

| Check | Target | Action if Failed |
|-------|--------|------------------|
| Beam centering | < 1mm offset | Adjust mirrors |
| Fringe visibility | > 80% contrast | Clean optics, check coherence |
| SLM response | Linear phase | Calibrate LUT |
| CCD noise floor | < 1% signal | Check grounding, exposure |

### 4.2 Baseline Verification

**Procedure:**
1. Write single test pattern (no superposition)
2. Immediately read back
3. Calculate γ

**Requirement:** γ ≥ 0.95

**If failed:** Do not proceed. Debug optical path.

---

## 5. Test Protocol

### 5.1 Phase A: Superposition Write

**Objective:** Establish multi-pattern interference field

**Procedure:**
1. Initialize FPGA controller
2. For i = 1 to 50:
   - Generate spectrum vector (FFT of test data)
   - Apply phase modulation via SLM
   - Expose crystal (1-5 seconds per pattern)
   - Log write timestamp
3. Verify superposition (qualitative fringe pattern check)

**Acceptance:** Visible interference pattern on CCD

### 5.2 Phase B: Baseline Measurement

**Objective:** Measure initial γ before stress

**Procedure:**
1. Select target pattern (first write)
2. Generate low-energy probe (1% write power)
3. Capture CCD response
4. Compute γ via FPGA

**Record:** Initial γ (expect ≥ 0.85 for 50 patterns)

### 5.3 Phase C: Stress Injection

**Objective:** Apply controlled trauma to substrate

**Erasure Proxy:**
- Place physical mask over 25% of CCD sensor
- This simulates loss of spectral information

**Drift Injection:**
- Heat crystal mount to 40-50°C
- OR slightly rotate reference beam angle
- Target: 0.3-1.0 rad equivalent phase shift

**Measure:** Post-trauma γ (expect 0.15-0.40)

### 5.4 Phase D: Recovery Walk

**Objective:** Test controller recovery capability

**Procedure:**
1. Initialize recovery engine on FPGA
2. For iteration = 1 to 20:
   - Fire probe laser (1% power)
   - Capture CCD response
   - Compute current γ
   - Execute one phase correction pass
   - Log γ value
3. Record convergence curve

**Record:** γ at each iteration, total iterations to threshold

### 5.5 Phase E: Non-Destructive Read Test

**Objective:** Verify reads don't degrade substrate

**Procedure:**
1. Note current γ
2. Execute 100 consecutive probe cycles (no writes)
3. Measure γ after each batch of 10
4. Compute Δγ/read

**Requirement:** Δγ/read ≤ 0.001

**CRITICAL:** This is a hard architectural constraint. Failure disqualifies substrate.

---

## 6. Data Recording

### 6.1 Log Sheet Template

```
SSS Bench Log - Run ID: ___________
Date: ___________  Operator: ___________

A. Configuration
   Bands: [1024] [2048] [4096]  (circle one)
   Writes: _____
   Probe Power: _____ % of write
   Erasure Mask: _____ %
   Drift Method: [Thermal] [Angular]  (circle one)
   Drift Magnitude: _____ rad (measured)

B. Baseline
   Initial γ (clean): _____
   [ ] PASS (≥0.95)  [ ] FAIL

C. Post-Trauma
   γ after stress: _____
   Expected range: 0.15-0.40

D. Recovery Log
   Iter |  γ   | Δγ  | Notes
   -----|------|-----|------
     0  |      |  -  |
     1  |      |     |
     2  |      |     |
     ...
    15  |      |     |
    20  |      |     |

E. Non-Destructive Test
   Start γ: _____
   End γ (after 100 reads): _____
   Δγ/read: _____
   [ ] PASS (≤0.001)  [ ] FAIL

F. Verdict
   [ ] GO - All criteria met
   [ ] NO-GO - Redline triggered: ___________
```

### 6.2 Digital Data Format

Export raw γ values as CSV:

```csv
run_id,timestamp,iteration,gamma,delta_gamma,notes
RUN001,2024-01-15T10:30:00,0,0.152,,post-trauma
RUN001,2024-01-15T10:30:05,1,0.287,0.135,
RUN001,2024-01-15T10:30:10,2,0.401,0.114,
...
```

---

## 7. Success Criteria

### 7.1 Quantitative Criteria

| Metric | Requirement | Measurement |
|--------|-------------|-------------|
| Baseline γ | ≥ 0.95 | After calibration |
| Post-trauma γ | > 0 | After stress (proves non-locality) |
| Recovered γ | ≥ 0.70 | After ≤15 iterations |
| Convergence | Monotonic | No drops > 0.05 |
| Read decay | Δγ/read ≤ 0.001 | After 100 reads |

### 7.2 Qualitative Criteria

| Observation | Expectation |
|-------------|-------------|
| Recovery curve shape | Smooth climb, plateau near threshold |
| Convergence speed | Most gain in first 5-10 iterations |
| Response to erasure | Proportional γ drop, not catastrophic |

---

## 8. Comparison to Simulation

### 8.1 Expected Correspondence

| Simulator Prediction | Physical Expectation |
|---------------------|---------------------|
| γ ≈ 0.15-0.40 post-trauma | Within ±20% |
| γ ≈ 0.67-0.70 post-recovery | Within ±15% |
| Monotonic convergence | No reversals > 0.05 |
| <15 iterations to 0.7 | Within 2× |

### 8.2 Acceptable Deviation

Physical results may deviate from simulation due to:
- Optical noise not modeled
- Thermal coupling not modeled
- Material imperfections

**Acceptable:** Up to 20% deviation in γ values if shape matches

**Unacceptable:** Qualitative disagreement (chaos, collapse, decay)

---

## 9. Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Baseline γ < 0.9 | Optical misalignment | Realign, clean optics |
| No recovery | Algorithm bug | Check FPGA code |
| Oscillating γ | Unstable thermal | Add thermal control |
| Read decay | Wrong probe power | Reduce probe energy |
| Rapid saturation | Overexposure | Reduce write energy |

---

## 10. Post-Run Analysis

### 10.1 Immediate Analysis

1. Plot γ vs. iteration curve
2. Overlay with simulator prediction
3. Calculate deviation metrics
4. Check all pass/fail criteria

### 10.2 Documentation

1. Archive raw data (CSV + images)
2. Complete log sheet
3. Photograph rig setup
4. Note any anomalies

### 10.3 Decision

Based on results, determine:

- **GO:** Proceed to extended validation
- **NO-GO:** Identify failure mode, revise assumptions
- **INCONCLUSIVE:** Additional runs needed

---

## References

- See `falsification-brief.md` for kill-switch criteria
- See `../SPEC/coherence-model.md` for γ definition
- See `simulator.py` for comparison predictions
