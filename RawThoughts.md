# Simulations

Codex--> I updated the real defaults in simulator.py (line 40) and simulator.py (line 615) so both SimConfig and --bands now default to 4096.

Run	Bands	Erasure	Trials	Success Rate (γ >= 0.70)	Final γ
Previous PowerShell baseline	1024	25%	20	15%	median 0.6890
Full simulator run	4096	25%	1	n/a	0.6853
Focused stability probe	4096	25%	20	0%	median 0.6851
Killer probe	4096	50%	20	0%	median 0.5597
Killer probe single run	4096	50%	1	no	0.5621
The important part is that 4096 bands did not become the MVS at 50 writes. The standard --test all run still ended in VALIDATION SUMMARY: FAIL, because the recovery leg only reached γ = 0.6853, below the 0.70 threshold. Compared with the earlier 1024-band probe, the 25% erasure case did not improve to 100%; it actually came in at 0/20 successful recoveries in the repeated 4096-band trial set.

For the 50% killer test, the system still recovers above your approximate floor, but not into the recovery-safe zone. In other words, it does not collapse to the formal noise_floor, but it also does not recover identity robustly; it settles around γ ≈ 0.56.

The --plot run was launched in the background, and a python.exe process is active for it now. If the Matplotlib windows aren’t frontmost, they may just be behind other windows.

The evidence here points away from “more bands alone fixes stability” and toward the current limiter being the recovery dynamics and/or write density at 50 concurrent writes. The next best sweep is probably 4096 bands while varying num_writes, not substrate_size.


<img width="1170" height="773" alt="SSSvsNoise" src="https://github.com/user-attachments/assets/1d446437-95be-476e-99b0-81e4fbc56244" />

<img width="1251" height="711" alt="SSS_recovery performance" src="https://github.com/user-attachments/assets/10f0208b-dd44-4e79-97f5-1f4d4829de86" />



