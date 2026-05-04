---
name: Break the Model
about: Identify a condition where the SSS model fails or becomes invalid
title: "[BREAK] "
labels: break, validation
assignees: ""
---

## What are you trying to break?

Describe the specific assumption, claim, or mechanism you believe fails.

Examples:
- γ as a reachability invariant
- H_E as a separation metric
- Phase-walk convergence
- Non-destructive read assumption
- Distributed identity (non-locality)

---

## Failure Type

Select one:

- [ ] Structural (separation failure)
- [ ] Dynamic (selection failure)
- [ ] Physical (substrate constraint)
- [ ] Algorithmic (recovery failure)
- [ ] Conceptual (model inconsistency)

---

## Proposed Breaking Scenario

Describe the setup clearly:

- Parameters (α, N, D, SNR, etc.)
- Type of perturbation (noise, drift, erasure, etc.)
- Expected outcome

---

## Why this should break the model

Explain your reasoning:

- What assumption does this violate?
- Which part of the model fails?
- Is this a known edge case or a new one?

---

## Evidence (if available)

- Simulation results
- Plots
- Analytical argument
- External references

---

## Expected Outcome

What should happen if you're correct?

- [ ] Violates a redline (R1–R4)
- [ ] Breaks decision rule validity
- [ ] Produces contradiction between metrics
- [ ] Other (describe)

---

## Notes

This repository defines a **falsifiable model**.

Submissions that demonstrate failure under defined conditions are **valuable outcomes**, not bugs.

See HANDOFF/falsification-brief.md for the pre-declared redlines.

---
