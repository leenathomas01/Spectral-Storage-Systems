# SSS Attractor Model

**Document:** SPEC/attractor-model.md  
**Version:** 0.1  
**Status:** Theoretical — derived from collaborative development, awaiting
formal mathematical proof and simulation stress-testing

---

## 1. Why This Document Exists

The phase-diagram spec (`SPEC/phase-diagram.md`) defines the decision rule and
validation loop. It tells you *what* to measure and *when* memory is valid.

This document explains *why* those measurements work — the underlying
dynamical model that makes SSS coherent as an architecture rather than a
collection of useful metrics.

This framing was not in the prior specification. It emerged from
iterative stress-testing of the γ-only model, specifically from the
recognition that γ measures reachability but not identity. Once that
distinction was made, the attractor model became the natural explanation for
what the system is actually doing.

---

## 2. The Core Reframe

**Prior framing:**
> Data is stored as a spectral interference pattern. Recovery is phase
> correction toward a stored baseline.

**New framing (SSS):**
> Identities are attractors in a structured spectral manifold. Storage is
> basin shaping. Recovery behaves like gradient descent toward the correct
> energy minimum (approximated by phase-walk in the current implementation).

These are not contradictory. The attractor framing is the *why* underneath
the prior *what*. Phase-walk recovery is an approximation of gradient descent
in the energy landscape. The γ zones are descriptions of basin geometry.

---

## 3. The Four-Layer Stack

SSS validity rests on four layers, each necessary, none sufficient alone:

```
Layer 4 — Dynamical Layer
          Energy landscape over the spectral manifold.
          Governs identity stability under perturbation.
          What makes recovery work, not just what it does.

Layer 3 — Geometric Layer
          The spectral manifold M.
          The structured space where valid identities live.
          Defines the neighborhood structure that makes
          gradient descent meaningful.

Layer 2 — Separation Layer
          H_E, d_min, Δγ.
          Are the basins distinct enough to tell apart?
          This is the structural validity question.

Layer 1 — Signal Layer
          γ, SNR.
          Can the system reach an attractor at all?
          This is the reachability question.
```

**Common failure:** using Layer 1 metrics (γ, SNR) to answer Layer 2
questions (identity validity). This produces confident wrong answers — the
system converges cleanly to the wrong basin and γ ≈ 1.0 throughout.

H_E is the Layer 2 signal. correctness is the empirical check on Layer 4.

---

## 4. The Energy Landscape

Define the energy function over spectral response space:

```
E(R) = 1 - γ(R, Pᵢ*)
```

where Pᵢ* is the target identity pattern. Valid identities correspond to
minima of E(R). Recovery is minimization of E.

*Note: E(R) is a proxy energy function derived from correlation. It is not
a physically derived energy functional and is used for analytical intuition,
not as a physical claim.*

**Basin of attraction for identity i:**

```
B(Pᵢ) = { R : gradient descent on E converges to Pᵢ }
```

The γ integrity zones map directly to basin geometry:

| Zone | γ Range | Basin Description |
|------|---------|-------------------|
| High Fidelity | > 0.9 | Deep inside basin — steep walls, fast convergence |
| Coherence Drift | 0.7 – 0.9 | Near basin rim — gradient still points inward |
| Approximate | 0.4 – 0.7 | Saddle region between basins — probabilistic |
| Noise Floor | < 0.4 | Outside all basins — no gradient toward any identity |

These zones correspond to observed dynamical behavior in simulation.
Their exact equivalence to basin geometry is an active area of analysis,
not a proven result — see Section 9.

**Critical implication:** The transition from Coherence Drift to Approximate
is not a software parameter to tune. It is a property of the identity density
and codebook structure. You cannot push identities closer together and
maintain the same zone boundaries.

---

## 5. Phase-Walk as Gradient Descent

The phase-walk recovery algorithm (coordinate-wise phase correction) is an
approximation of gradient descent on E(R):

```
Rₜ₊₁ = Rₜ - η · ∇E(Rₜ)
```

Coordinate-wise correction is not full gradient descent — it updates one
spectral component at a time rather than all simultaneously. This is a
practical approximation that:

- Converges monotonically under normal conditions (verified in simulation)
- Is computationally cheap (per-band complex multiply)
- Can fail to escape shallow local minima (false coherence basins)

**The false coherence problem:**
If two identity basins overlap significantly, the landscape has a shallow
ridge between them. Phase-walk may converge to a point on that ridge rather
than either true minimum. γ will be moderate, H_E will be elevated.
This is structural failure (L2) not dynamic failure (L4).

The fix is not better optimization — it is better basin separation (higher α,
lower ρ = N/D).

---

## 6. Stability Under Write

Each new identity written into the system creates a new energy minimum and
deforms the existing landscape. The stability question is:

*Does writing Pₙₑw reduce the basin depth or curvature of existing
identities Pᵢ (i < n)?*

This is the spectral analog of catastrophic forgetting in neural networks.

**Three failure regimes as density increases:**

```
Sparse (ρ << ρ_crit):
  Basins are well-separated.
  Writing Pₙₑw creates a new minimum without significantly
  deforming existing ones.
  H_E remains low. All identities valid.

Near-critical (ρ ≈ ρ_crit):
  Basins begin to overlap at their edges.
  New writes cause existing basins to shallow.
  H_E increases. Some identities become ambiguous.

Dense (ρ >> ρ_crit):
  Basin overlap is severe.
  The landscape flattens into a near-uniform surface.
  H_E is high even at γ ≈ 1.0. No identities reliably valid.
```

The capacity surface plots show this empirically. α_crit is the codebook
parameter that most controls where ρ_crit falls for a given N/D.

---

## 7. What Graceful Degradation Actually Means

Under substrate damage (erasure, drift, noise), the energy landscape deforms:

- Erasure removes spectral components → basins become shallower
- Phase drift rotates the landscape → basins shift position
- Noise adds stochastic perturbation → effective probe position smears

**The graceful degradation claim:**
For moderate damage, basin depth decreases proportionally rather than
catastrophically. The system can still converge — just with more iterations,
and with higher risk of landing near a basin boundary.

This is what the simulator validated in v0.4:
- 25% erasure → γ drops but recovery is possible
- 1.2 rad drift → within pull-in envelope of phase-walk

**The limit:**
Once basin overlap becomes severe (from damage or density), the landscape
transitions from "deformed but navigable" to "flat." This is the R4 redline
in the falsification brief (`HANDOFF/falsification-brief.md`) — the point where graceful degradation
becomes catastrophic forgetting.

---

## 8. Identity Is Reached, Not Stored

The deepest reframe:

In address-based storage, identity is a location. Data is *at* an address.
Damage to that location means loss of that data.

In SSS, identity is a dynamical state. Data *corresponds to* an attractor.
Damage deforms the landscape but does not destroy the attractor — unless
damage is severe enough to eliminate the basin entirely.

This is why the architecture absorbs noise rather than merely tolerating it.
A noisy probe does not retrieve a corrupted version of the data. It starts
a trajectory in a deformed landscape and converges — with some probability
and some latency cost — to the correct attractor.

**Formal statement:**

> An identity in SSS is not stored at a location. It is encoded as a stable
> fixed point of the recovery dynamics. Retrieval is not lookup — it is
> convergence.

---

## 9. Open Questions

This document formalizes what is currently understood. The following remain
open and are the natural next targets for simulation or proof:

**Q1: Basin curvature preservation under sequential writes**
How does curvature of existing basins change as N increases? Is degradation
monotonic? Is there a sharp transition?

**Q2: Phase-walk escape probability**
Under what conditions can phase-walk escape a false coherence basin? Does
adding momentum help, and what is the cost in iterations?

**Q3: Optimal codebook geometry for basin separation**
Fourier codebooks provide an upper bound on orthogonality. What is the
relationship between codebook structure and basin separation in the energy
landscape?

**Q4: Physical landscape correspondence**
The energy landscape is currently defined over idealized complex vectors.
Does a physical substrate (LiNbO₃ or equivalent) produce a landscape with
the same basin structure? This is the physical falsification question.

---

## 10. Relationship to Other Documents

- `SPEC/phase-diagram.md` — the decision rule that this model explains
- `SPEC/coherence-model.md` — the metric definitions (γ, H_E, correctness)
- `VALIDATION/STATUS.md` — what has been empirically confirmed
- `HANDOFF/falsification-brief.md` — the physical redlines derived from
  the basin stability model
