> Raw thoughts/ runs before polishing


---
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

---

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
