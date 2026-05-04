# PRIOR/IVSA

This directory contains the full original IVSA (Interference-Based Volumetric
Storage Architecture) specification, preserved for lineage and reference.

## What IVSA Was

IVSA was the predecessor to SSS. It introduced the core ideas:

- Spectral interference as the storage primitive
- Correlation Coherence (γ) as the integrity metric
- Phase-walk recovery as the controller algorithm
- LiNbO₃ as the reference physical substrate
- Explicit kill-switches (redlines) for falsification

## Why SSS Supersedes It

The key change: IVSA used γ as the primary validity metric. SSS recognized
that γ measures reachability only — a system can converge cleanly (γ ≈ 1.0)
while selecting the wrong identity or failing to separate identities.

SSS introduced H_E (identity energy entropy) and correctness as the true
validity signals, demoting γ to a diagnostic input.

The physical substrate model, bench protocol, and redlines from IVSA are
preserved and remain valid pending physical testing.

## Files

- `architecture.md` — core invariants and system model
- `coherence-model.md` — original γ-based coherence model (superseded)
- `controller-logic.md` — signal flow specification
- `mvs-constraints.md` — minimum viable substrate requirements

## Current Location of Active Specs

- `SPEC/` — current SSS specifications
- `HANDOFF/` — bench protocol, falsification brief, engineering FAQ
