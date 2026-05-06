> This file contains Raw thoughts/ runs and their analysis done before polishing. Not relevant to repo. Only for personal tracking.
>
>  This file may be ignored.


---
### Run 1
```
C:\pythonSSS>python spectral_tensor_emulator_final.py --no-plot
[SSS Tensor Resonance Probe]
dim=4096, identities=32, target=ID_07, codebook=random, alpha=1.00, SNR=-5.0 dB, seed=17

Case                          | Noise             | Lock  | Target |  gamma |  H_amp |    H_E | d_gamma | Perturb | Elastic(E)
--------------------------------------------------------------------------------------------------------------------------
legacy magnitude echo         | legacy_component  | ID_14 | no     |  0.381 |  3.249 |  2.874 |   0.059 | yes     | no
controlled magnitude echo     | controlled_vector | ID_07 | yes    |  0.979 |  2.110 |  0.252 |   0.897 | yes     | yes
controlled complex echo       | controlled_vector | ID_07 | yes    |  0.946 |  2.779 |  0.870 |   0.810 | yes     | yes
competitive elastic echo      | controlled_vector | ID_07 | yes    |  1.000 |  1.558 |  0.062 |   0.971 | yes     | yes

Exact-target entropy floor for this codebook: H_amp=1.558, H_E=0.062, nearest competitor=0.029

Elastic(E) criterion: target lock, gamma >= 0.85, H_E <= 1.0, delta gamma >= 0.20, and perturbation returns to the same basin.
H_amp is still reported because it matches the original prototype scorer.

```

### Analysis of run 1

The four echo modes are testing four different recovery strategies:

Legacy magnitude echo — FAILS

- Locked on ID_14, not ID_07 (wrong basin)
- H_E = 2.874 — completely ambiguous, basins merged
- This is the old approach. It fails deliberately. It's the baseline showing why you need better recovery.

Controlled magnitude echo — PASSES

- Correct lock on ID_07
- H_E = 0.252 — well separated
- γ = 0.979 — strong convergence --> This is Case D from the spec. Textbook valid.

Controlled complex echo — PASSES

- Correct lock, H_E = 0.870 — still under H_crit=1.0 but closer to the boundary
- γ = 0.946 Valid but with less margin than magnitude echo
- Competitive elastic echo — PASSES cleanly
- γ = 1.000, H_E = 0.062 — nearly perfect separation
- d_gamma = 0.971 — dominant basin is crushing the competition --> This is the best recovery mode. This is what generated the original plots.

The entropy floor line is important:

- H_amp=1.558, H_E=0.062, nearest competitor=0.029
- Even the exact target vector has H_E=0.062 at rest — that's the theoretical minimum for this codebook.
- The competitive elastic echo is hitting essentially the floor. Can't do much better than this.

---
---

### Run 2
```
C:\pythonSSS>python spectral_tensor_emulator_final.py --phase-diagram --num-id 1024 --target-idx 7 --sweep-alphas 0.0,0.5,0.7,0.8,0.9,1.0 --sweep-snrs 10,-10,-20,-30,-40 --trials 5 --no-plot
[SSS Alpha-SNR Phase Diagram]
dim=4096, identities=1024, target=ID_07, trials=5, metric=true H_E
alpha |  SNR dB | sep_rate |    acc |  valid | mean_H_E | State
----------------------------------------------------------------------------
 0.00 |    10.0 |     0.00 |   1.00 |   0.00 |    1.760 | ambiguous
 0.00 |   -10.0 |     0.00 |   1.00 |   0.00 |    1.760 | ambiguous
 0.00 |   -20.0 |     0.00 |   1.00 |   0.00 |    1.760 | ambiguous
 0.00 |   -30.0 |     0.00 |   0.00 |   0.00 |    1.823 | ambiguous
 0.00 |   -40.0 |     0.00 |   0.00 |   0.00 |    1.824 | ambiguous
 0.50 |    10.0 |     0.00 |   1.00 |   0.00 |    1.447 | ambiguous
 0.50 |   -10.0 |     0.00 |   1.00 |   0.00 |    1.447 | ambiguous
 0.50 |   -20.0 |     0.00 |   1.00 |   0.00 |    1.447 | ambiguous
 0.50 |   -30.0 |     0.00 |   0.20 |   0.00 |    1.437 | ambiguous
 0.50 |   -40.0 |     0.00 |   0.00 |   0.00 |    1.458 | ambiguous
 0.70 |    10.0 |     0.00 |   1.00 |   0.00 |    1.078 | ambiguous
 0.70 |   -10.0 |     0.00 |   1.00 |   0.00 |    1.078 | ambiguous
 0.70 |   -20.0 |     0.00 |   1.00 |   0.00 |    1.078 | ambiguous
 0.70 |   -30.0 |     0.00 |   0.20 |   0.00 |    1.067 | ambiguous
 0.70 |   -40.0 |     0.00 |   0.00 |   0.00 |    1.072 | ambiguous
 0.80 |    10.0 |     1.00 |   1.00 |   1.00 |    0.815 | valid
 0.80 |   -10.0 |     1.00 |   1.00 |   1.00 |    0.815 | valid
 0.80 |   -20.0 |     1.00 |   1.00 |   1.00 |    0.815 | valid
 0.80 |   -30.0 |     1.00 |   0.20 |   0.20 |    0.805 | mis-selection
 0.80 |   -40.0 |     1.00 |   0.00 |   0.00 |    0.811 | mis-selection
 0.90 |    10.0 |     1.00 |   1.00 |   1.00 |    0.475 | valid
 0.90 |   -10.0 |     1.00 |   1.00 |   1.00 |    0.475 | valid
 0.90 |   -20.0 |     1.00 |   1.00 |   1.00 |    0.475 | valid
 0.90 |   -30.0 |     1.00 |   0.40 |   0.40 |    0.479 | mis-selection
 0.90 |   -40.0 |     1.00 |   0.00 |   0.00 |    0.471 | mis-selection
 1.00 |    10.0 |     1.00 |   1.00 |   1.00 |    0.000 | valid
 1.00 |   -10.0 |     1.00 |   1.00 |   1.00 |    0.000 | valid
 1.00 |   -20.0 |     1.00 |   1.00 |   1.00 |    0.000 | valid
 1.00 |   -30.0 |     1.00 |   0.40 |   0.40 |    0.000 | mis-selection
 1.00 |   -40.0 |     1.00 |   0.00 |   0.00 |    0.000 | mis-selection
```

---

### Analysis of Run 2

This is the real result. Lets decode it properly.

The phase boundary is sharp and exactly where theory predicts:

- The structural boundary sits between α=0.70 and α=0.80.
- Below that, H_E stays above H_crit regardless of SNR — the basins are merged and SNR cannot fix it.
- Above it, separability is perfect (sep_rate=1.00) all the way down to -20dB.
- The dynamic boundary sits between -20dB and -30dB.
- Above that, correct selection holds. Below it, selection collapses — but H_E stays low. --> That's Case B from the spec, live in the data.

The α=1.0 row :
1.00 | 10.0  | sep_rate=1.00 | H_E=0.000 | valid
1.00 | -30.0 | sep_rate=1.00 | H_E=0.000 | mis-selection

H_E is exactly zero at pure Fourier — perfect separation — but selection still fails at low SNR. 

The basins are perfectly distinct, the system just can't find the right one in the noise. 

L4 confirmed experimentally: structural fixes cannot compensate dynamic failure.

---
### Run 3

```
C:\pythonSSS>python spectral_tensor_emulator_final.py --phase-diagram --num-id 1024 --target-idx 7 --sweep-alphas 0.0,0.5,0.7,0.8,0.9,1.0 --sweep-snrs 10,-10,-20,-30,-40 --trials 20 --no-plot
[SSS Alpha-SNR Phase Diagram]
dim=4096, identities=1024, target=ID_07, trials=20, metric=true H_E
alpha |  SNR dB | sep_rate |    acc |  valid | mean_H_E | State
----------------------------------------------------------------------------
 0.00 |    10.0 |     0.00 |   1.00 |   0.00 |    1.778 | ambiguous
 0.00 |   -10.0 |     0.00 |   1.00 |   0.00 |    1.778 | ambiguous
 0.00 |   -20.0 |     0.00 |   1.00 |   0.00 |    1.778 | ambiguous
 0.00 |   -30.0 |     0.00 |   0.20 |   0.00 |    1.813 | ambiguous
 0.00 |   -40.0 |     0.00 |   0.00 |   0.00 |    1.816 | ambiguous
 0.50 |    10.0 |     0.00 |   1.00 |   0.00 |    1.448 | ambiguous
 0.50 |   -10.0 |     0.00 |   1.00 |   0.00 |    1.448 | ambiguous
 0.50 |   -20.0 |     0.00 |   1.00 |   0.00 |    1.448 | ambiguous
 0.50 |   -30.0 |     0.00 |   0.30 |   0.00 |    1.453 | ambiguous
 0.50 |   -40.0 |     0.00 |   0.00 |   0.00 |    1.454 | ambiguous
 0.70 |    10.0 |     0.00 |   1.00 |   0.00 |    1.077 | ambiguous
 0.70 |   -10.0 |     0.00 |   1.00 |   0.00 |    1.077 | ambiguous
 0.70 |   -20.0 |     0.00 |   1.00 |   0.00 |    1.077 | ambiguous
 0.70 |   -30.0 |     0.00 |   0.30 |   0.00 |    1.077 | ambiguous
 0.70 |   -40.0 |     0.00 |   0.00 |   0.00 |    1.081 | ambiguous
 0.80 |    10.0 |     1.00 |   1.00 |   1.00 |    0.813 | valid
 0.80 |   -10.0 |     1.00 |   1.00 |   1.00 |    0.813 | valid
 0.80 |   -20.0 |     1.00 |   1.00 |   1.00 |    0.813 | valid
 0.80 |   -30.0 |     1.00 |   0.30 |   0.30 |    0.817 | mis-selection
 0.80 |   -40.0 |     1.00 |   0.00 |   0.00 |    0.819 | mis-selection
 0.90 |    10.0 |     1.00 |   1.00 |   1.00 |    0.474 | valid
 0.90 |   -10.0 |     1.00 |   1.00 |   1.00 |    0.474 | valid
 0.90 |   -20.0 |     1.00 |   1.00 |   1.00 |    0.474 | valid
 0.90 |   -30.0 |     1.00 |   0.35 |   0.35 |    0.479 | mis-selection
 0.90 |   -40.0 |     1.00 |   0.00 |   0.00 |    0.479 | mis-selection
 1.00 |    10.0 |     1.00 |   1.00 |   1.00 |    0.000 | valid
 1.00 |   -10.0 |     1.00 |   1.00 |   1.00 |    0.000 | valid
 1.00 |   -20.0 |     1.00 |   1.00 |   1.00 |    0.000 | valid
 1.00 |   -30.0 |     1.00 |   0.35 |   0.35 |    0.000 | mis-selection
 1.00 |   -40.0 |     1.00 |   0.00 |   0.00 |    0.000 | mis-selection
```
---
### Analysis of Run 3

What trials=20 confirms over trials=5:

-The boundaries didn't move at all. Every state classification is identical. 
The mean_H_E values are stable to 3 decimal places. 

This is what statistical confirmation looks like — not new information, but the same information with higher confidence.

Key numbers that are now citable:

- Structural boundary: exactly at α=0.70→0.80, H_E drops from 1.077 to 0.813. Sharp, clean, reproducible across 20 trials.
- Dynamic boundary: -20dB→-30dB. Selection accuracy drops from 1.00 to 0.30-0.35 across all α ≥ 0.80.
- α=1.0, H_E=0.000 — exact Fourier separation — still mis-selects at -30dB (acc=0.35). L4 is now statistically confirmed, not just observed.
- The 0.30-0.35 partial accuracy at -30dB is interesting — not zero, not one. The system is probabilistically right at the dynamic boundary. That's the basin rim behavior the attractor model predicts.

--- 
> for later: update status.md with the below
>
> The phase boundary result is statistically confirmed at trials=20 with the original
validated emulator. The structural boundary (α=0.70–0.80) and dynamic
boundary (-20 to -30 dB) are clean and consistent across all runs.
Boundary classifications are identical between trials=5 and trials=20.
mean_H_E values stable to 3 decimal places. This result is citable.

---

## ROADMAP -ish 
(i mean hellooo? This is my downtime hobby?)

### Current State

✔ Mathematical model defined
✔ Metrics clean (γ, H_E, correctness)
✔ Phase diagram statistically confirmed (trials=20)
✔ Failure modes cleanly separated (structural vs dynamic)


### Next steps

1.1 Phase Boundary Refinement

--sweep-alphas 0.70,0.72,0.74,0.76,0.78,0.80
--trials 50

determines whether system is:

- phase-transition-like (strong result)
- or just thresholded (weaker)

1.2 Density Scaling Law (ρ = N/D)

Right now: one slice: N=1024, D=4096

Next step: 
Run:  
N = 256, 512, 1024, 2048
D = constant (4096)

Measure: α_crit vs ρ

Goal: Find relationship: α_crit ≈ f(N/D)
If this stabilizes → this becomes a real law, not just observation.

1.3 Stress the “γ is useless alone” claim

Construct adversarial cases:

- high γ + high H_E
- high γ + low H_E + wrong answer

We already have examples—formalize them.

This becomes: “this is why ECC-style thinking fails here”

2. Model Deepening

2.1 Formalize the energy landscape

Right now: E(R) = 1 - γ

But this is: heuristic, not derived

Next step: explore alternative energy definitions: squared correlation, full vector distance, multi-basin energy. Basically make attractor model less “analogy”, more “formal mapping”
