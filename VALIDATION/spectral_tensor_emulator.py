"""
Spectral Storage Systems tensor resonance probe.

This file is a NumPy equivalent of the proposed PyTorch IVSATensorEmulator.
It tests whether echo dynamics can enter an "elastic" spectral regime:

1. gamma crosses 0.85.
2. entropy collapses below 1.0.
3. winner margin, delta gamma, exceeds 0.20.
4. a phase perturbation returns to the same identity basin.

The probe also includes the legacy component-wise noise model from the pasted
prototype. That model is intentionally retained as a diagnostic because it
scales noise with sqrt(dim), making the effective SNR far harsher than the
nominal dB value suggests.

Two entropy readouts are reported:

- H_amp: entropy over raw correlation amplitudes, matching the prototype.
- H_energy: entropy over squared correlations, closer to field energy.

H_amp has a nonzero random-codebook floor: even an exact target vector has
small residual correlations with other random identities. H_energy is usually
the better "collapse" diagnostic for a spectral field.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


EPSILON = 1e-12
GAMMA_THRESHOLD = 0.85
ENTROPY_THRESHOLD = 1.0
MARGIN_THRESHOLD = 0.20


@dataclass(frozen=True)
class TensorConfig:
    dim: int = 4096
    num_id: int = 32
    target_idx: int = 7
    seed: int = 17
    codebook: str = "random"
    coherence_alpha: float = 1.0
    snr_db: float = -5.0
    iterations: int = 25
    perturb_iterations: int = 8
    phase_noise_std: float = 0.30


@dataclass(frozen=True)
class ExperimentCase:
    name: str
    mode: str
    noise_model: str
    lr: float
    perturb_lr: float
    power: float = 1.0
    sharpness: float = 1.0


@dataclass(frozen=True)
class Metrics:
    iteration: int
    max_gamma: float
    max_idx: int
    amp_entropy: float
    energy_entropy: float
    delta_gamma: float


def complex_normal(rng: np.random.Generator, shape: int | tuple[int, ...]) -> np.ndarray:
    """Unit-variance circular complex Gaussian samples."""
    real = rng.normal(size=shape)
    imag = rng.normal(size=shape)
    return (real + 1j * imag) / math.sqrt(2.0)


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm <= EPSILON:
        raise ValueError("Cannot normalize a near-zero vector.")
    return vector / norm


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp_values = np.exp(shifted)
    return exp_values / (np.sum(exp_values) + EPSILON)


class SpectralTensorEmulator:
    def __init__(self, config: TensorConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)

        self.identities = self._build_identities(config)
        self.target_pattern = self.identities[config.target_idx]

    def _build_identities(self, config: TensorConfig) -> np.ndarray:
        if config.codebook == "random":
            return self._random_identities(config)

        if config.codebook == "fourier":
            return self._fourier_identities(config)

        if config.codebook == "hybrid":
            alpha = min(1.0, max(0.0, config.coherence_alpha))
            fourier = self._fourier_identities(config)
            random = self._random_identities(config)
            mixed = math.sqrt(alpha) * fourier + math.sqrt(1.0 - alpha) * random
            norms = np.linalg.norm(mixed, axis=1, keepdims=True)
            return mixed / np.maximum(norms, EPSILON)

        raise ValueError(f"Unknown codebook: {config.codebook}")

    def _random_identities(self, config: TensorConfig) -> np.ndarray:
        raw_ids = complex_normal(self.rng, (config.num_id, config.dim))
        norms = np.linalg.norm(raw_ids, axis=1, keepdims=True)
        return raw_ids / np.maximum(norms, EPSILON)

    def _fourier_identities(self, config: TensorConfig) -> np.ndarray:
        if config.num_id > config.dim:
            raise ValueError("Fourier codebook requires num_id <= dim.")
        freqs = np.arange(config.num_id, dtype=np.float64)[:, None]
        bins = np.arange(config.dim, dtype=np.float64)[None, :]
        phases = 2.0 * np.pi * freqs * bins / float(config.dim)
        return np.exp(1j * phases) / math.sqrt(config.dim)

    def get_overlaps(self, probe: np.ndarray) -> np.ndarray:
        return self.identities.conj() @ probe

    def get_correlations(self, probe: np.ndarray) -> np.ndarray:
        return np.abs(self.get_overlaps(probe))

    def calc_entropy(self, correlations: np.ndarray) -> tuple[float, np.ndarray]:
        probs = correlations / (np.sum(correlations) + EPSILON)
        entropy = -np.sum(probs * np.log(probs + EPSILON))
        return float(entropy), probs

    def make_noisy_probe(self, noise_model: str, snr_db: float) -> np.ndarray:
        noise_amp = 10.0 ** (-snr_db / 20.0)

        if noise_model == "controlled_vector":
            # Vector-level SNR: the whole noise field has the requested power.
            noise = normalize(complex_normal(self.rng, self.config.dim))
        elif noise_model == "legacy_component":
            # Prototype-compatible SNR: every component receives that amplitude.
            # In high dimensions this floods the target by roughly sqrt(dim).
            noise = complex_normal(self.rng, self.config.dim)
        else:
            raise ValueError(f"Unknown noise model: {noise_model}")

        return normalize(self.target_pattern + noise_amp * noise)

    def substrate_response(self, probe: np.ndarray, case: ExperimentCase) -> np.ndarray:
        overlaps = self.get_overlaps(probe)
        correlations = np.abs(overlaps)

        if case.mode == "magnitude":
            # Original-style echo. This intentionally discards complex phase.
            weights = correlations.astype(np.complex128)
        elif case.mode == "complex":
            # Phase-preserving projection into the identity subspace.
            weights = overlaps
        elif case.mode == "competitive":
            # Attraction plus exclusion: phase-preserving weights are sharpened
            # so the dominant basin suppresses diffuse competitors.
            scaled = correlations / (np.max(correlations) + EPSILON)
            competition = softmax(case.sharpness * scaled)
            gate = np.power(np.maximum(scaled, EPSILON), case.power)
            weights = overlaps * competition * gate
        else:
            raise ValueError(f"Unknown response mode: {case.mode}")

        response = self.identities.T @ weights
        return normalize(response)

    def measure(self, probe: np.ndarray, iteration: int) -> Metrics:
        correlations = self.get_correlations(probe)
        amp_entropy, _ = self.calc_entropy(correlations)
        energy_entropy, _ = self.calc_entropy(correlations * correlations)
        order = np.argsort(correlations)
        max_idx = int(order[-1])
        max_gamma = float(correlations[max_idx])
        runner_up = float(correlations[order[-2]]) if len(order) > 1 else 0.0
        return Metrics(
            iteration=iteration,
            max_gamma=max_gamma,
            max_idx=max_idx,
            amp_entropy=amp_entropy,
            energy_entropy=energy_entropy,
            delta_gamma=max_gamma - runner_up,
        )

    def converge(
        self,
        initial_probe: np.ndarray,
        case: ExperimentCase,
        iterations: int,
        lr: float,
    ) -> tuple[np.ndarray, list[Metrics]]:
        probe = initial_probe.copy()
        history: list[Metrics] = []

        for iteration in range(iterations + 1):
            history.append(self.measure(probe, iteration))
            if iteration == iterations:
                break

            echo = self.substrate_response(probe, case)
            anneal = max(0.25, 1.0 - math.sqrt(iteration / max(iterations, 1)))
            probe = normalize(probe + (lr * anneal) * (echo - probe))

        return probe, history


def run_case(config: TensorConfig, case: ExperimentCase) -> dict[str, object]:
    emulator = SpectralTensorEmulator(config)
    initial_probe = emulator.make_noisy_probe(case.noise_model, config.snr_db)
    initial_metrics = emulator.measure(initial_probe, 0)

    final_probe, history = emulator.converge(
        initial_probe=initial_probe,
        case=case,
        iterations=config.iterations,
        lr=case.lr,
    )
    final_metrics = history[-1]

    phase_noise = np.exp(
        1j * emulator.rng.normal(scale=config.phase_noise_std, size=config.dim)
    )
    disturbed = normalize(final_probe * phase_noise)
    _, recovery_history = emulator.converge(
        initial_probe=disturbed,
        case=case,
        iterations=config.perturb_iterations,
        lr=case.perturb_lr,
    )
    recovery_metrics = recovery_history[-1]

    target_locked = final_metrics.max_idx == config.target_idx
    perturb_same = recovery_metrics.max_idx == final_metrics.max_idx
    raw_elastic = (
        target_locked
        and final_metrics.max_gamma >= GAMMA_THRESHOLD
        and final_metrics.amp_entropy <= ENTROPY_THRESHOLD
        and final_metrics.delta_gamma >= MARGIN_THRESHOLD
        and perturb_same
    )
    energy_elastic = (
        target_locked
        and final_metrics.max_gamma >= GAMMA_THRESHOLD
        and final_metrics.energy_entropy <= ENTROPY_THRESHOLD
        and final_metrics.delta_gamma >= MARGIN_THRESHOLD
        and perturb_same
    )

    return {
        "case": case,
        "initial": initial_metrics,
        "final": final_metrics,
        "recovery": recovery_metrics,
        "target_floor": emulator.measure(emulator.target_pattern, 0),
        "target_locked": target_locked,
        "perturb_same": perturb_same,
        "raw_elastic": raw_elastic,
        "energy_elastic": energy_elastic,
        "history": history,
        "recovery_history": recovery_history,
    }


def default_cases() -> list[ExperimentCase]:
    return [
        ExperimentCase(
            name="legacy magnitude echo",
            mode="magnitude",
            noise_model="legacy_component",
            lr=0.15,
            perturb_lr=0.10,
        ),
        ExperimentCase(
            name="controlled magnitude echo",
            mode="magnitude",
            noise_model="controlled_vector",
            lr=0.20,
            perturb_lr=0.12,
        ),
        ExperimentCase(
            name="controlled complex echo",
            mode="complex",
            noise_model="controlled_vector",
            lr=0.35,
            perturb_lr=0.20,
        ),
        ExperimentCase(
            name="competitive elastic echo",
            mode="competitive",
            noise_model="controlled_vector",
            lr=0.70,
            perturb_lr=0.45,
            power=2.0,
            sharpness=10.0,
        ),
    ]


def competitive_case() -> ExperimentCase:
    return ExperimentCase(
        name="competitive elastic echo",
        mode="competitive",
        noise_model="controlled_vector",
        lr=0.70,
        perturb_lr=0.45,
        power=2.0,
        sharpness=10.0,
    )


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def print_summary(config: TensorConfig, results: list[dict[str, object]]) -> None:
    print("[SSS Tensor Resonance Probe]")
    print(
        f"dim={config.dim}, identities={config.num_id}, target=ID_{config.target_idx:02d}, "
        f"codebook={config.codebook}, alpha={config.coherence_alpha:.2f}, "
        f"SNR={config.snr_db:.1f} dB, seed={config.seed}"
    )
    print()
    print(
        f"{'Case':<29} | {'Noise':<17} | {'Lock':<5} | {'Target':<6} | "
        f"{'gamma':>6} | {'H_amp':>6} | {'H_E':>6} | {'d_gamma':>7} | "
        f"{'Perturb':<7} | {'Elastic(E)'}"
    )
    print("-" * 122)

    for result in results:
        case = result["case"]
        final = result["final"]
        assert isinstance(case, ExperimentCase)
        assert isinstance(final, Metrics)
        print(
            f"{case.name:<29} | {case.noise_model:<17} | ID_{final.max_idx:02d} | "
            f"{yes_no(bool(result['target_locked'])):<6} | {final.max_gamma:6.3f} | "
            f"{final.amp_entropy:6.3f} | {final.energy_entropy:6.3f} | "
            f"{final.delta_gamma:7.3f} | "
            f"{yes_no(bool(result['perturb_same'])):<7} | "
            f"{yes_no(bool(result['energy_elastic']))}"
        )

    first_result = results[0] if results else None
    if first_result is not None:
        target_floor = first_result["target_floor"]
        assert isinstance(target_floor, Metrics)
        print()
        print(
            "Exact-target entropy floor for this codebook: "
            f"H_amp={target_floor.amp_entropy:.3f}, "
            f"H_E={target_floor.energy_entropy:.3f}, "
            f"nearest competitor={target_floor.max_gamma - target_floor.delta_gamma:.3f}"
        )

    print()
    print(
        "Elastic(E) criterion: target lock, gamma >= 0.85, H_E <= 1.0, "
        "delta gamma >= 0.20, and perturbation returns to the same basin."
    )
    print("H_amp is still reported because it matches the original prototype scorer.")


def parse_alpha_values(raw_values: str) -> list[float]:
    values: list[float] = []
    for raw in raw_values.split(","):
        value = float(raw.strip())
        if value < 0.0 or value > 1.0:
            raise ValueError("Sweep alpha values must stay in [0.0, 1.0].")
        values.append(value)
    return values


def parse_int_values(raw_values: str) -> list[int]:
    values: list[int] = []
    for raw in raw_values.split(","):
        value = int(raw.strip())
        if value <= 0:
            raise ValueError("Sweep identity counts must be positive.")
        values.append(value)
    return values


def parse_float_values(raw_values: str) -> list[float]:
    values: list[float] = []
    for raw in raw_values.split(","):
        values.append(float(raw.strip()))
    return values


def run_coherence_sweep(config: TensorConfig, alpha_values: list[float]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    case = competitive_case()

    print("[SSS Controlled-Coherence Sweep]")
    print(
        f"dim={config.dim}, identities={config.num_id}, target=ID_{config.target_idx:02d}, "
        f"SNR={config.snr_db:.1f} dB, seed={config.seed}"
    )
    print(
        f"{'alpha':>5} | {'floor_H_E':>9} | {'floor_comp':>10} | {'gamma':>6} | "
        f"{'H_E':>6} | {'d_gamma':>7} | {'Perturb':<7} | {'Elastic(E)'}"
    )
    print("-" * 86)

    for alpha in alpha_values:
        sweep_config = TensorConfig(
            dim=config.dim,
            num_id=config.num_id,
            target_idx=config.target_idx,
            seed=config.seed,
            codebook="hybrid",
            coherence_alpha=alpha,
            snr_db=config.snr_db,
            iterations=config.iterations,
            perturb_iterations=config.perturb_iterations,
            phase_noise_std=config.phase_noise_std,
        )
        result = run_case(sweep_config, case)
        final = result["final"]
        target_floor = result["target_floor"]
        assert isinstance(final, Metrics)
        assert isinstance(target_floor, Metrics)
        floor_competitor = target_floor.max_gamma - target_floor.delta_gamma

        print(
            f"{alpha:5.2f} | {target_floor.energy_entropy:9.3f} | "
            f"{floor_competitor:10.3f} | {final.max_gamma:6.3f} | "
            f"{final.energy_entropy:6.3f} | {final.delta_gamma:7.3f} | "
            f"{yes_no(bool(result['perturb_same'])):<7} | "
            f"{yes_no(bool(result['energy_elastic']))}"
        )
        results.append({"alpha": alpha, **result})

    first_fail = next(
        (
            result
            for result in sorted(results, key=lambda item: float(item["alpha"]), reverse=True)
            if not bool(result["energy_elastic"])
        ),
        None,
    )
    last_pass = next(
        (
            result
            for result in sorted(results, key=lambda item: float(item["alpha"]))
            if bool(result["energy_elastic"])
        ),
        None,
    )

    print()
    if first_fail is None:
        print("No Elastic(E) failure observed across the sampled alpha range.")
    elif last_pass is None:
        print("No Elastic(E) pass observed across the sampled alpha range.")
    else:
        print(
            "Sampled boundary: Elastic(E) fails by "
            f"alpha={float(first_fail['alpha']):.2f} and recovers by "
            f"alpha={float(last_pass['alpha']):.2f}."
        )

    return results


def run_snr_sweep(config: TensorConfig, snr_values: list[float]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    case = competitive_case()

    print("[SSS SNR Sweep]")
    print(
        f"dim={config.dim}, identities={config.num_id}, target=ID_{config.target_idx:02d}, "
        f"codebook={config.codebook}, alpha={config.coherence_alpha:.2f}, seed={config.seed}"
    )
    print(
        f"{'SNR dB':>7} | {'Lock':<7} | {'Target':<6} | {'gamma':>6} | "
        f"{'H_E':>6} | {'d_gamma':>7} | {'Perturb':<7} | {'Elastic(E)'}"
    )
    print("-" * 84)

    for snr_db in snr_values:
        sweep_config = TensorConfig(
            dim=config.dim,
            num_id=config.num_id,
            target_idx=config.target_idx,
            seed=config.seed,
            codebook=config.codebook,
            coherence_alpha=config.coherence_alpha,
            snr_db=snr_db,
            iterations=config.iterations,
            perturb_iterations=config.perturb_iterations,
            phase_noise_std=config.phase_noise_std,
        )
        result = run_case(sweep_config, case)
        final = result["final"]
        assert isinstance(final, Metrics)

        print(
            f"{snr_db:7.1f} | ID_{final.max_idx:04d} | "
            f"{yes_no(bool(result['target_locked'])):<6} | {final.max_gamma:6.3f} | "
            f"{final.energy_entropy:6.3f} | {final.delta_gamma:7.3f} | "
            f"{yes_no(bool(result['perturb_same'])):<7} | "
            f"{yes_no(bool(result['energy_elastic']))}"
        )
        results.append({"snr_db": snr_db, **result})

    return results


def run_phase_diagram(
    config: TensorConfig,
    alpha_values: list[float],
    snr_values: list[float],
    trials: int,
) -> list[dict[str, object]]:
    if trials <= 0:
        raise ValueError("Phase diagram trials must be positive.")

    results: list[dict[str, object]] = []
    case = competitive_case()

    print("[SSS Alpha-SNR Phase Diagram]")
    print(
        f"dim={config.dim}, identities={config.num_id}, target=ID_{config.target_idx:02d}, "
        f"trials={trials}, metric=true H_E"
    )
    print(
        f"{'alpha':>5} | {'SNR dB':>7} | {'sep_rate':>8} | {'acc':>6} | "
        f"{'valid':>6} | {'mean_H_E':>8} | {'State'}"
    )
    print("-" * 76)

    for alpha in alpha_values:
        for snr_db in snr_values:
            separable_count = 0
            correct_count = 0
            valid_count = 0
            entropy_values: list[float] = []

            for trial in range(trials):
                trial_config = TensorConfig(
                    dim=config.dim,
                    num_id=config.num_id,
                    target_idx=config.target_idx,
                    seed=config.seed + trial,
                    codebook="hybrid",
                    coherence_alpha=alpha,
                    snr_db=snr_db,
                    iterations=config.iterations,
                    perturb_iterations=config.perturb_iterations,
                    phase_noise_std=config.phase_noise_std,
                )
                result = run_case(trial_config, case)
                final = result["final"]
                assert isinstance(final, Metrics)

                separable = final.energy_entropy <= ENTROPY_THRESHOLD
                correct = bool(result["target_locked"])
                valid = separable and correct

                separable_count += int(separable)
                correct_count += int(correct)
                valid_count += int(valid)
                entropy_values.append(final.energy_entropy)

            separable_rate = separable_count / trials
            accuracy = correct_count / trials
            valid_rate = valid_count / trials
            mean_entropy = float(np.mean(entropy_values))

            if separable_rate < 0.5:
                state = "ambiguous"
                state_code = 0
            elif valid_rate >= 0.5:
                state = "valid"
                state_code = 2
            else:
                state = "mis-selection"
                state_code = 1

            print(
                f"{alpha:5.2f} | {snr_db:7.1f} | {separable_rate:8.2f} | "
                f"{accuracy:6.2f} | {valid_rate:6.2f} | {mean_entropy:8.3f} | {state}"
            )

            results.append(
                {
                    "alpha": alpha,
                    "snr_db": snr_db,
                    "separable_rate": separable_rate,
                    "accuracy": accuracy,
                    "valid_rate": valid_rate,
                    "mean_energy_entropy": mean_entropy,
                    "state": state,
                    "state_code": state_code,
                    "trials": trials,
                }
            )

    return results


def run_capacity_sweep(
    config: TensorConfig,
    alpha_values: list[float],
    identity_counts: list[int],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    case = competitive_case()

    print("[SSS Capacity Surface Sweep]")
    print(
        f"dim={config.dim}, SNR={config.snr_db:.1f} dB, seed={config.seed}, "
        f"metric=true H_E"
    )
    print(
        f"{'N':>5} | {'alpha':>5} | {'floor_H_E':>9} | {'gamma':>6} | "
        f"{'H_E':>6} | {'d_gamma':>7} | {'Elastic(E)'}"
    )
    print("-" * 70)

    for num_id in identity_counts:
        if num_id > config.dim:
            raise ValueError("Identity count cannot exceed dim for hybrid/Fourier codebooks.")

        target_idx = config.target_idx % num_id
        for alpha in alpha_values:
            sweep_config = TensorConfig(
                dim=config.dim,
                num_id=num_id,
                target_idx=target_idx,
                seed=config.seed,
                codebook="hybrid",
                coherence_alpha=alpha,
                snr_db=config.snr_db,
                iterations=config.iterations,
                perturb_iterations=config.perturb_iterations,
                phase_noise_std=config.phase_noise_std,
            )
            result = run_case(sweep_config, case)
            final = result["final"]
            target_floor = result["target_floor"]
            assert isinstance(final, Metrics)
            assert isinstance(target_floor, Metrics)

            print(
                f"{num_id:5d} | {alpha:5.2f} | {target_floor.energy_entropy:9.3f} | "
                f"{final.max_gamma:6.3f} | {final.energy_entropy:6.3f} | "
                f"{final.delta_gamma:7.3f} | {yes_no(bool(result['energy_elastic']))}"
            )
            results.append({"num_id": num_id, "alpha": alpha, **result})

    print()
    for num_id in identity_counts:
        series = [
            result
            for result in results
            if int(result["num_id"]) == num_id and bool(result["energy_elastic"])
        ]
        if not series:
            print(f"N={num_id}: no Elastic(E) pass in sampled alpha range.")
            continue
        alpha_crit = min(float(result["alpha"]) for result in series)
        print(f"N={num_id}: sampled alpha_crit <= {alpha_crit:.2f}")

    return results


def save_sweep_plot(results: list[dict[str, object]], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        print(f"Sweep plot skipped: matplotlib unavailable ({exc}).")
        return

    alphas = [float(result["alpha"]) for result in results]
    final_entropy = []
    floor_entropy = []
    gamma = []
    competitor = []

    for result in results:
        final = result["final"]
        target_floor = result["target_floor"]
        assert isinstance(final, Metrics)
        assert isinstance(target_floor, Metrics)
        final_entropy.append(final.energy_entropy)
        floor_entropy.append(target_floor.energy_entropy)
        gamma.append(final.max_gamma)
        competitor.append(target_floor.max_gamma - target_floor.delta_gamma)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    axes[0].plot(alphas, gamma, marker="o", label="final gamma")
    axes[0].plot(alphas, competitor, marker="o", label="exact-target competitor")
    axes[0].axhline(GAMMA_THRESHOLD, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Coherence vs lock quality")
    axes[0].set_xlabel("Fourier energy fraction alpha")
    axes[0].set_ylabel("correlation")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].plot(alphas, final_entropy, marker="o", label="final H_E")
    axes[1].plot(alphas, floor_entropy, marker="o", label="exact-target H_E floor")
    axes[1].axhline(ENTROPY_THRESHOLD, color="black", linestyle="--", linewidth=1)
    axes[1].set_title("Coherence vs entropy floor")
    axes[1].set_xlabel("Fourier energy fraction alpha")
    axes[1].set_ylabel("H_E")
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.suptitle("SSS controlled-coherence sweep", fontsize=13)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"Sweep plot saved: {out_path}")


def save_capacity_plot(results: list[dict[str, object]], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        print(f"Capacity plot skipped: matplotlib unavailable ({exc}).")
        return

    fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
    identity_counts = sorted({int(result["num_id"]) for result in results})

    for num_id in identity_counts:
        series = sorted(
            [result for result in results if int(result["num_id"]) == num_id],
            key=lambda item: float(item["alpha"]),
        )
        alphas = [float(result["alpha"]) for result in series]
        entropy = []
        for result in series:
            final = result["final"]
            assert isinstance(final, Metrics)
            entropy.append(final.energy_entropy)
        ax.plot(alphas, entropy, marker="o", linewidth=2, label=f"N={num_id}")

    ax.axhline(ENTROPY_THRESHOLD, color="black", linestyle="--", linewidth=1.5)
    ax.set_title("SSS Capacity Boundary: True Energy Entropy vs Coherence")
    ax.set_xlabel("Fourier energy fraction alpha")
    ax.set_ylabel("Final H_E")
    ax.grid(alpha=0.25)
    ax.legend()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"Capacity plot saved: {out_path}")


def save_snr_plot(results: list[dict[str, object]], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        print(f"SNR plot skipped: matplotlib unavailable ({exc}).")
        return

    snrs = [float(result["snr_db"]) for result in results]
    gamma = []
    entropy = []

    for result in results:
        final = result["final"]
        assert isinstance(final, Metrics)
        gamma.append(final.max_gamma)
        entropy.append(final.energy_entropy)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    axes[0].plot(snrs, gamma, marker="o", linewidth=2)
    axes[0].axhline(GAMMA_THRESHOLD, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("SNR vs lock quality")
    axes[0].set_xlabel("SNR dB")
    axes[0].set_ylabel("final gamma")
    axes[0].grid(alpha=0.25)

    axes[1].plot(snrs, entropy, marker="o", linewidth=2)
    axes[1].axhline(ENTROPY_THRESHOLD, color="black", linestyle="--", linewidth=1)
    axes[1].set_title("SNR vs identity entropy")
    axes[1].set_xlabel("SNR dB")
    axes[1].set_ylabel("final H_E")
    axes[1].grid(alpha=0.25)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.suptitle("SSS SNR sweep", fontsize=13)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"SNR plot saved: {out_path}")


def save_phase_diagram_plot(results: list[dict[str, object]], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        print(f"Phase diagram plot skipped: matplotlib unavailable ({exc}).")
        return

    alphas = sorted({float(result["alpha"]) for result in results})
    snrs = sorted({float(result["snr_db"]) for result in results})
    state_grid = np.zeros((len(snrs), len(alphas)))
    valid_grid = np.zeros((len(snrs), len(alphas)))
    entropy_grid = np.zeros((len(snrs), len(alphas)))

    alpha_index = {value: idx for idx, value in enumerate(alphas)}
    snr_index = {value: idx for idx, value in enumerate(snrs)}

    for result in results:
        row = snr_index[float(result["snr_db"])]
        col = alpha_index[float(result["alpha"])]
        state_grid[row, col] = int(result["state_code"])
        valid_grid[row, col] = float(result["valid_rate"])
        entropy_grid[row, col] = float(result["mean_energy_entropy"])

    cmap = ListedColormap(["#d84a3a", "#e9b949", "#2f9e44"])
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)

    extent = [
        min(alphas) - 0.5 * _grid_step(alphas),
        max(alphas) + 0.5 * _grid_step(alphas),
        min(snrs) - 0.5 * _grid_step(snrs),
        max(snrs) + 0.5 * _grid_step(snrs),
    ]

    im0 = axes[0].imshow(
        state_grid,
        origin="lower",
        aspect="auto",
        cmap=cmap,
        vmin=0,
        vmax=2,
        extent=extent,
    )
    axes[0].set_title("Dominant state")
    colorbar = fig.colorbar(im0, ax=axes[0], ticks=[0, 1, 2])
    colorbar.ax.set_yticklabels(["ambiguous", "mis-select", "valid"])

    im1 = axes[1].imshow(
        valid_grid,
        origin="lower",
        aspect="auto",
        cmap="Greens",
        vmin=0,
        vmax=1,
        extent=extent,
    )
    axes[1].set_title("P(valid)")
    fig.colorbar(im1, ax=axes[1])

    im2 = axes[2].imshow(
        entropy_grid,
        origin="lower",
        aspect="auto",
        cmap="magma_r",
        extent=extent,
    )
    axes[2].set_title("mean H_E")
    fig.colorbar(im2, ax=axes[2])

    for axis in axes:
        axis.set_xlabel("Fourier energy fraction alpha")
        axis.set_ylabel("SNR dB")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.suptitle("SSS alpha-SNR phase diagram", fontsize=13)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"Phase diagram plot saved: {out_path}")


def _grid_step(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    ordered = sorted(values)
    return min(
        abs(ordered[index + 1] - ordered[index])
        for index in range(len(ordered) - 1)
    )


def save_plot(config: TensorConfig, results: list[dict[str, object]], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - diagnostic fallback
        print(f"Plot skipped: matplotlib unavailable ({exc}).")
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)

    for result in results:
        case = result["case"]
        history = result["history"]
        assert isinstance(case, ExperimentCase)
        assert isinstance(history, list)

        x = [metric.iteration for metric in history]
        gamma = [metric.max_gamma for metric in history]
        entropy = [metric.energy_entropy for metric in history]

        axes[0].plot(x, gamma, marker="o", linewidth=1.8, markersize=3, label=case.name)
        axes[1].plot(x, entropy, marker="o", linewidth=1.8, markersize=3, label=case.name)

    axes[0].axhline(GAMMA_THRESHOLD, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Correlation coherence")
    axes[0].set_xlabel("Iteration")
    axes[0].set_ylabel("max gamma")
    axes[0].grid(alpha=0.25)

    axes[1].axhline(ENTROPY_THRESHOLD, color="black", linestyle="--", linewidth=1)
    axes[1].set_title("Identity energy entropy")
    axes[1].set_xlabel("Iteration")
    axes[1].set_ylabel("H_E")
    axes[1].grid(alpha=0.25)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.08))
    fig.suptitle(
        f"SSS tensor resonance probe: {config.num_id} identities in {config.dim} bands",
        fontsize=13,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"Plot saved: {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dim", type=int, default=4096)
    parser.add_argument("--num-id", type=int, default=32)
    parser.add_argument("--target-idx", type=int, default=7)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--codebook", choices=("random", "fourier", "hybrid"), default="random")
    parser.add_argument("--coherence-alpha", type=float, default=1.0)
    parser.add_argument("--snr-db", type=float, default=-5.0)
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--sweep-coherence", action="store_true")
    parser.add_argument("--sweep-capacity", action="store_true")
    parser.add_argument("--sweep-snr", action="store_true")
    parser.add_argument("--phase-diagram", action="store_true")
    parser.add_argument(
        "--sweep-alphas",
        default="1.0,0.95,0.9,0.8,0.7,0.6,0.5,0.25,0.0",
        help="Comma-separated alpha values for --sweep-coherence.",
    )
    parser.add_argument(
        "--sweep-ns",
        default="32,256,512,1024",
        help="Comma-separated identity counts for --sweep-capacity.",
    )
    parser.add_argument(
        "--sweep-snrs",
        default="30,20,10,0,-5,-10,-20,-30,-40",
        help="Comma-separated SNR dB values for --sweep-snr.",
    )
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--no-plot", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = TensorConfig(
        dim=args.dim,
        num_id=args.num_id,
        target_idx=args.target_idx,
        seed=args.seed,
        codebook=args.codebook,
        coherence_alpha=args.coherence_alpha,
        snr_db=args.snr_db,
        iterations=args.iterations,
    )

    if args.sweep_coherence:
        sweep_results = run_coherence_sweep(config, parse_alpha_values(args.sweep_alphas))
        if not args.no_plot:
            save_sweep_plot(
                sweep_results,
                Path("VALIDATION") / "spectral_coherence_sweep.png",
            )
        return

    if args.sweep_capacity:
        capacity_results = run_capacity_sweep(
            config,
            parse_alpha_values(args.sweep_alphas),
            parse_int_values(args.sweep_ns),
        )
        if not args.no_plot:
            save_capacity_plot(
                capacity_results,
                Path("VALIDATION") / "spectral_capacity_surface.png",
            )
        return

    if args.sweep_snr:
        snr_results = run_snr_sweep(config, parse_float_values(args.sweep_snrs))
        if not args.no_plot:
            save_snr_plot(
                snr_results,
                Path("VALIDATION") / "spectral_snr_sweep.png",
            )
        return

    if args.phase_diagram:
        phase_results = run_phase_diagram(
            config,
            parse_alpha_values(args.sweep_alphas),
            parse_float_values(args.sweep_snrs),
            args.trials,
        )
        if not args.no_plot:
            save_phase_diagram_plot(
                phase_results,
                Path("VALIDATION") / "spectral_phase_diagram.png",
            )
        return

    results = [run_case(config, case) for case in default_cases()]
    print_summary(config, results)

    if not args.no_plot:
        save_plot(config, results, Path("VALIDATION") / "spectral_tensor_emulator.png")


if __name__ == "__main__":
    main()
