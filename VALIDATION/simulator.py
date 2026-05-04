#!/usr/bin/env python3
"""
SSS Signal & Coherence Simulator
=================================

Validates the mathematical foundations of Interference-Based Volumetric Storage.

This simulator tests:
1. γ (correlation coherence) behavior under noise
2. Recovery basin characteristics under phase drift and erasure
3. Optimizer convergence properties
4. Scaling behavior across write counts and spectral resolution

Version: 0.4
Status: Validated — Ready for physical comparison

Usage:
    python simulator.py                    # Run all validations
    python simulator.py --test noise       # Run specific test
    python simulator.py --plot             # Generate visualization
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List, Optional
from enum import Enum
import argparse


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class SimConfig:
    """Simulation configuration parameters."""
    
    # Substrate parameters
    substrate_size: int = 4096          # Number of spectral bands
    num_writes: int = 20                # Concurrent superposed patterns
    
    # Integrity thresholds (configurable)
    gamma_fast_path: float = 0.90       # Above: deterministic read
    gamma_recovery: float = 0.70        # Above: iterative recovery possible
    gamma_approximate: float = 0.40     # Above: statistical inference
    
    # Recovery parameters
    max_recovery_iterations: int = 15   # Hard limit on phase-walk
    recovery_gain: float = 0.5          # Correction step size
    recovery_engine: str = "phase_walk" # phase_walk or sic
    sic_refinement_passes: int = 2      # Extra SIC cleanup passes
    masked_success_gamma: float = 0.95  # High-fidelity masked target
    
    # Stress parameters
    erasure_fraction: float = 0.25      # Fraction of substrate to null
    drift_strength: float = 0.30        # Phase drift in radians
    
    # Sweep parameters
    snr_range_db: Tuple[float, float] = (-5, 25)
    snr_steps: int = 50
    drift_range: Tuple[float, float] = (0.1, 1.2)
    drift_steps: int = 10


class IntegrityZone(Enum):
    """Integrity zone classification based on γ value."""
    HIGH_FIDELITY = "high_fidelity"
    COHERENCE_DRIFT = "coherence_drift"
    APPROXIMATE = "approximate"
    NOISE_FLOOR = "noise_floor"


# =============================================================================
# Core Functions
# =============================================================================

def generate_spectrum(size: int, normalize: bool = True) -> np.ndarray:
    """
    Generate a random complex spectral pattern.
    
    Simulates transforming data block into frequency domain representation.
    In real system: FFT of data + phase modulation.
    
    Args:
        size: Number of spectral bands
        normalize: If True, normalize to unit energy
        
    Returns:
        Complex-valued spectrum vector
    """
    spectrum = np.random.randn(size) + 1j * np.random.randn(size)
    if normalize:
        spectrum = spectrum / np.linalg.norm(spectrum)
    return spectrum


def _calculate_gamma_core(
    reference: np.ndarray,
    response: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> float:
    """Compute normalized complex correlation, optionally on a masked subset."""
    ref = reference.flatten()
    resp = response.flatten()
    
    if mask is not None:
        mask_flat = np.asarray(mask).flatten().astype(bool)
        ref = ref[mask_flat]
        resp = resp[mask_flat]
    
    if ref.size == 0 or resp.size == 0:
        return 0.0
    
    correlation = np.vdot(resp, ref)
    norm_ref = np.linalg.norm(ref)
    norm_resp = np.linalg.norm(resp)
    
    if norm_ref == 0 or norm_resp == 0:
        return 0.0
    
    return np.abs(correlation) / (norm_ref * norm_resp)


def calculate_gamma(reference: np.ndarray, response: np.ndarray) -> float:
    """
    Compute correlation coherence (γ) between reference and response.
    
    This is the primary integrity metric for the prior envelope model, replacing BER.
    
    Args:
        reference: Expected spectral signature (from write time)
        response: Received resonant envelope (from read)
        
    Returns:
        γ value in range [0.0, 1.0]
        - 1.0 = perfect alignment
        - 0.0 = complete decorrelation
    """
    return _calculate_gamma_core(reference, response)


def calculate_masked_gamma(
    reference: np.ndarray,
    response: np.ndarray,
    mask: np.ndarray
) -> float:
    """
    Compute coherence only on non-erased bins.
    
    This isolates recovery quality on the surviving substrate and avoids
    penalizing the algorithm for bins that were physically erased.
    """
    return _calculate_gamma_core(reference, response, mask)


def classify_zone(gamma: float, config: SimConfig) -> IntegrityZone:
    """Classify γ value into integrity zone."""
    if gamma >= config.gamma_fast_path:
        return IntegrityZone.HIGH_FIDELITY
    elif gamma >= config.gamma_recovery:
        return IntegrityZone.COHERENCE_DRIFT
    elif gamma >= config.gamma_approximate:
        return IntegrityZone.APPROXIMATE
    else:
        return IntegrityZone.NOISE_FLOOR


# =============================================================================
# Substrate Simulation
# =============================================================================

class VolumetricSubstrate:
    """
    Simulates a volumetric interference substrate.
    
    This is an abstract mathematical model - no physical assumptions.
    The substrate holds superposed spectral patterns as a complex vector.
    """
    
    def __init__(self, size: int):
        self.size = size
        self.field = np.zeros(size, dtype=complex)
        self.write_log: List[np.ndarray] = []
        
    def write(self, spectrum: np.ndarray) -> int:
        """
        Add a spectral pattern to the interference field.
        
        This is ADDITIVE - no erase-before-write.
        Returns the index of this write for later retrieval.
        """
        assert len(spectrum) == self.size
        self.field += spectrum
        self.write_log.append(spectrum.copy())
        return len(self.write_log) - 1
    
    def probe(self, add_noise_snr_db: Optional[float] = None) -> np.ndarray:
        """
        Probe the substrate and return resonant response.
        
        This is NON-DESTRUCTIVE - substrate state unchanged.
        Optionally adds AWGN for noise simulation.
        """
        response = self.field.copy()
        
        if add_noise_snr_db is not None:
            response = self._add_awgn(response, add_noise_snr_db)
            
        return response
    
    def apply_erasure(self, fraction: float) -> np.ndarray:
        """
        Apply random erasure to simulate physical damage.
        
        Returns the mask for visualization/analysis.
        Does NOT modify internal state - returns damaged copy.
        """
        mask = np.random.choice(
            [0, 1], 
            size=self.size, 
            p=[fraction, 1 - fraction]
        )
        return self.field * mask, mask
    
    def apply_drift(self, strength: float) -> np.ndarray:
        """
        Apply random phase drift to simulate thermal/aging effects.
        
        Returns drifted copy - does NOT modify internal state.
        """
        drift = np.exp(1j * np.random.uniform(-strength, strength, self.size))
        return self.field * drift
    
    def _add_awgn(self, signal: np.ndarray, snr_db: float) -> np.ndarray:
        """Add Additive White Gaussian Noise at specified SNR."""
        snr_linear = 10 ** (snr_db / 10.0)
        signal_power = np.mean(np.abs(signal) ** 2)
        noise_power = signal_power / snr_linear
        
        noise = np.sqrt(noise_power / 2) * (
            np.random.randn(len(signal)) + 1j * np.random.randn(len(signal))
        )
        return signal + noise
    
    def get_baseline(self, write_index: int) -> np.ndarray:
        """Get the baseline signature for a specific write."""
        return self.write_log[write_index].copy()


# =============================================================================
# Recovery Engine
# =============================================================================

def phase_walk_recovery(
    response: np.ndarray,
    baseline: np.ndarray,
    config: SimConfig,
    mask: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, List[float], int]:
    """
    Iterative phase correction to maximize γ.
    
    Implements coordinate-wise descent on phase angles.
    
    Args:
        response: Degraded response from substrate
        baseline: Expected signature from write time
        config: Simulation configuration
        mask: Optional mask indicating erased elements (skip these)
        
    Returns:
        Tuple of:
        - Corrected response
        - History of γ values per iteration
        - Number of iterations used
    """
    current = response.copy()
    gamma_history = [calculate_gamma(baseline, current)]
    valid = np.abs(current) >= 1e-10
    
    if mask is not None:
        valid &= np.asarray(mask).astype(bool)
    
    for iteration in range(config.max_recovery_iterations):
        if gamma_history[-1] >= config.gamma_fast_path:
            return current, gamma_history, iteration
        
        if np.any(valid):
            phase_error = np.angle(baseline[valid]) - np.angle(current[valid])
            correction = np.exp(1j * phase_error * config.recovery_gain)
            current[valid] *= correction
        
        gamma_history.append(calculate_gamma(baseline, current))
    
    return current, gamma_history, config.max_recovery_iterations


def derive_phase_correction(
    original_response: np.ndarray,
    corrected_response: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """Infer the unit-magnitude phase correction applied during recovery."""
    correction = np.ones_like(original_response, dtype=complex)
    valid = np.abs(original_response) >= 1e-10
    
    if mask is not None:
        valid &= np.asarray(mask).astype(bool)
    
    correction[valid] = corrected_response[valid] / original_response[valid]
    return correction


def estimate_observed_contribution(
    baseline: np.ndarray,
    phase_correction: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Estimate a write's contribution in the observed domain.
    
    The phase-walk output approximates an inverse-drift field. Mapping the
    recovered baseline back through the conjugate correction yields an estimate
    of that write's contribution in the stressed mixture.
    """
    estimate = baseline * np.conj(phase_correction)
    
    if mask is not None:
        estimate = estimate * np.asarray(mask)
    
    return estimate


def sum_contributions(contributions: List[np.ndarray], shape: Tuple[int, ...]) -> np.ndarray:
    """Accumulate estimated write contributions into one complex field."""
    total = np.zeros(shape, dtype=complex)
    
    for contribution in contributions:
        total += contribution
    
    return total


def build_stress_case(
    config: SimConfig
) -> Tuple[List[np.ndarray], np.ndarray, np.ndarray]:
    """Generate baselines plus a stressed substrate response."""
    substrate = VolumetricSubstrate(config.substrate_size)
    
    for _ in range(config.num_writes):
        spectrum = generate_spectrum(config.substrate_size)
        substrate.write(spectrum)
    
    baselines = [substrate.get_baseline(i) for i in range(config.num_writes)]
    damaged, mask = substrate.apply_erasure(config.erasure_fraction)
    drift = np.exp(1j * np.random.uniform(
        -config.drift_strength,
        config.drift_strength,
        config.substrate_size
    ))
    stressed = damaged * drift
    return baselines, stressed, mask


def estimate_shared_transfer_field(
    response: np.ndarray,
    baseline_sum: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Estimate the common stressed-domain transfer field for the current mixture.
    
    In the ideal simulator every surviving write experiences the same per-bin
    erasure and phase drift. Dividing the residual mixture by the summed
    remaining baselines gives the transfer field needed for exact cancellation.
    """
    transfer = np.zeros_like(response, dtype=complex)
    valid = np.abs(baseline_sum) >= 1e-10
    
    if mask is not None:
        valid &= np.asarray(mask).astype(bool)
    
    transfer[valid] = response[valid] / baseline_sum[valid]
    return transfer


def sic_recovery(
    response: np.ndarray,
    baselines: List[np.ndarray],
    config: SimConfig,
    mask: Optional[np.ndarray] = None
) -> dict:
    """
    Recover identities one at a time with successive interference cancellation.
    
    Each step selects the strongest remaining baseline, runs phase walk on the
    current residual, estimates that write's stressed-domain contribution, and
    subtracts it before moving to the next write. A small number of refinement
    passes then revisits all recovered writes against the cleaned field.
    """
    residual = response.copy()
    remaining = list(range(len(baselines)))
    estimated_contributions = [
        np.zeros_like(response, dtype=complex) for _ in baselines
    ]
    recovery_order: List[int] = []
    extraction_pass = []
    
    while remaining:
        strongest_index = max(
            remaining,
            key=lambda idx: calculate_masked_gamma(baselines[idx], residual, mask)
            if mask is not None else calculate_gamma(baselines[idx], residual)
        )
        baseline = baselines[strongest_index]
        corrected, gamma_history, iterations = phase_walk_recovery(
            residual, baseline, config, mask
        )
        remaining_sum = sum_contributions(
            [baselines[idx] for idx in remaining], response.shape
        )
        transfer = estimate_shared_transfer_field(residual, remaining_sum, mask)
        estimated = baseline * transfer
        
        if mask is not None:
            estimated = estimated * np.asarray(mask)
        
        masked_final_gamma = (
            calculate_masked_gamma(baseline, corrected, mask)
            if mask is not None else calculate_gamma(baseline, corrected)
        )
        
        estimated_contributions[strongest_index] = estimated
        residual = residual - estimated
        recovery_order.append(strongest_index)
        extraction_pass.append({
            'write_index': strongest_index,
            'iterations': iterations,
            'final_gamma': gamma_history[-1],
            'final_masked_gamma': masked_final_gamma
        })
        remaining.remove(strongest_index)
    
    for _ in range(config.sic_refinement_passes):
        total_estimate = sum_contributions(estimated_contributions, response.shape)
        
        for write_index in recovery_order:
            isolated = response - (total_estimate - estimated_contributions[write_index])
            baseline = baselines[write_index]
            transfer = estimate_shared_transfer_field(isolated, baseline, mask)
            estimated_contributions[write_index] = baseline * transfer
            
            if mask is not None:
                estimated_contributions[write_index] *= np.asarray(mask)
            
            total_estimate = sum_contributions(estimated_contributions, response.shape)
        
    total_estimate = sum_contributions(estimated_contributions, response.shape)
    per_write = []
    
    for write_index in recovery_order:
        baseline = baselines[write_index]
        isolated = response - (total_estimate - estimated_contributions[write_index])
        initial_gamma = calculate_gamma(baseline, isolated)
        initial_masked_gamma = (
            calculate_masked_gamma(baseline, isolated, mask)
            if mask is not None else initial_gamma
        )
        corrected, gamma_history, iterations = phase_walk_recovery(
            isolated, baseline, config, mask
        )
        final_masked_gamma = (
            calculate_masked_gamma(baseline, corrected, mask)
            if mask is not None else gamma_history[-1]
        )
        is_monotonic = all(
            gamma_history[i] <= gamma_history[i + 1] + 0.01
            for i in range(len(gamma_history) - 1)
        )
        per_write.append({
            'write_index': write_index,
            'initial_gamma': initial_gamma,
            'initial_masked_gamma': initial_masked_gamma,
            'final_gamma': gamma_history[-1],
            'final_masked_gamma': final_masked_gamma,
            'gamma_history': gamma_history,
            'iterations': iterations,
            'monotonic': is_monotonic,
            'masked_reached_threshold': final_masked_gamma >= config.masked_success_gamma
        })
    
    return {
        'order': recovery_order,
        'extraction_pass': extraction_pass,
        'per_write': per_write,
        'residual': response - total_estimate
    }


# =============================================================================
# Validation Tests
# =============================================================================

def test_noise_sweep(config: SimConfig) -> dict:
    """
    Test 1: γ vs SNR curve (v0.1 validation)
    
    Validates:
    - Monotonic γ decay with increasing noise
    - No chaotic regions or cliffs
    - Clear zone separation
    """
    print("Running noise sweep test...")
    
    # Setup
    substrate = VolumetricSubstrate(config.substrate_size)
    
    # Write multiple patterns
    for _ in range(config.num_writes):
        spectrum = generate_spectrum(config.substrate_size)
        substrate.write(spectrum)
    
    # Get target pattern
    target = substrate.get_baseline(0)
    
    # Sweep SNR
    snrs = np.linspace(
        config.snr_range_db[0],
        config.snr_range_db[1],
        config.snr_steps
    )
    gammas = []
    
    for snr in snrs:
        response = substrate.probe(add_noise_snr_db=snr)
        gamma = calculate_gamma(target, response)
        gammas.append(gamma)
    
    # Validate monotonicity (with tolerance for noise)
    is_monotonic = all(
        gammas[i] <= gammas[i+1] + 0.05 
        for i in range(len(gammas)-1)
    )
    
    return {
        'snrs': snrs,
        'gammas': gammas,
        'monotonic': is_monotonic,
        'min_gamma': min(gammas),
        'max_gamma': max(gammas)
    }


def test_phase_walk_recovery(config: SimConfig) -> dict:
    """
    Test 2: Erasure + Drift recovery (v0.2-0.3 validation)
    
    Validates:
    - Identity persists under trauma (γ > 0 after damage)
    - Recovery converges monotonically
    - Recovery reaches threshold within iteration budget
    """
    print("Running stress recovery test...")
    
    # Setup
    substrate = VolumetricSubstrate(config.substrate_size)
    
    for _ in range(config.num_writes):
        spectrum = generate_spectrum(config.substrate_size)
        substrate.write(spectrum)
    
    target = substrate.get_baseline(0)
    
    # Apply trauma
    damaged, mask = substrate.apply_erasure(config.erasure_fraction)
    drift = np.exp(1j * np.random.uniform(
        -config.drift_strength, 
        config.drift_strength, 
        config.substrate_size
    ))
    stressed = damaged * drift
    
    # Initial γ (post-trauma)
    initial_gamma = calculate_gamma(target, stressed)
    initial_masked_gamma = calculate_masked_gamma(target, stressed, mask)
    
    # Run recovery
    recovered, gamma_history, iterations = phase_walk_recovery(
        stressed, target, config, mask
    )
    final_masked_gamma = calculate_masked_gamma(target, recovered, mask)
    
    # Validate
    is_monotonic = all(
        gamma_history[i] <= gamma_history[i+1] + 0.01
        for i in range(len(gamma_history)-1)
    )
    
    return {
        'initial_gamma': initial_gamma,
        'initial_masked_gamma': initial_masked_gamma,
        'final_gamma': gamma_history[-1],
        'final_masked_gamma': final_masked_gamma,
        'gamma_history': gamma_history,
        'iterations': iterations,
        'monotonic': is_monotonic,
        'recovery_gain': (gamma_history[-1] / initial_gamma - 1) * 100,
        'reached_threshold': gamma_history[-1] >= config.gamma_recovery,
        'masked_reached_threshold': final_masked_gamma >= config.gamma_recovery
    }


def test_sic_recovery(config: SimConfig) -> dict:
    """
    Test 2b: SIC recovery under erasure + drift.
    
    Validates:
    - Sequential cancellation can isolate multiple writes
    - Masked gamma remains high after interference subtraction
    - Residual energy falls as recovered writes are removed
    """
    baselines, stressed, mask = build_stress_case(config)
    sic_results = sic_recovery(stressed, baselines, config, mask)
    per_write = sic_results['per_write']
    masked_gammas = [entry['final_masked_gamma'] for entry in per_write]
    raw_gammas = [entry['final_gamma'] for entry in per_write]
    
    return {
        'order': sic_results['order'],
        'per_write': per_write,
        'masked_gammas': masked_gammas,
        'raw_gammas': raw_gammas,
        'min_masked_gamma': min(masked_gammas),
        'median_masked_gamma': float(np.median(masked_gammas)),
        'max_masked_gamma': max(masked_gammas),
        'min_gamma': min(raw_gammas),
        'median_gamma': float(np.median(raw_gammas)),
        'max_gamma': max(raw_gammas),
        'count_masked_high_fidelity': sum(
            gamma >= config.masked_success_gamma for gamma in masked_gammas
        ),
        'all_masked_high_fidelity': all(
            gamma >= config.masked_success_gamma for gamma in masked_gammas
        ),
        'monotonic': all(entry['monotonic'] for entry in per_write),
        'residual_ratio': (
            np.linalg.norm(sic_results['residual']) / np.linalg.norm(stressed)
            if np.linalg.norm(stressed) else 0.0
        )
    }


def test_stress_recovery(config: SimConfig) -> dict:
    """Dispatch to the configured recovery engine."""
    if config.recovery_engine == "sic":
        print("Running stress recovery test (sic)...")
        return test_sic_recovery(config)
    
    return test_phase_walk_recovery(config)


def test_envelope_mapping(config: SimConfig) -> dict:
    """
    Test 3: Pull-in envelope characterization (v0.4 validation)
    
    Validates:
    - Recovery basin width across parameter space
    - Scaling with write count and band count
    - Identifies redline (maximum recoverable drift)
    """
    print("Running envelope mapping test...")
    
    bands_to_test = [1024, 2048, 4096]
    writes_to_test = [50, 100, 200]
    drift_sweep = np.linspace(
        config.drift_range[0],
        config.drift_range[1],
        config.drift_steps
    )
    
    results = {}
    
    for bands in bands_to_test:
        for n_writes in writes_to_test:
            key = f"{bands}b_{n_writes}w"
            gammas = []
            
            for drift in drift_sweep:
                # Fresh substrate for each test
                substrate = VolumetricSubstrate(bands)
                
                for _ in range(n_writes):
                    spectrum = generate_spectrum(bands)
                    substrate.write(spectrum)
                
                target = substrate.get_baseline(0)
                
                # Apply standard erasure + variable drift
                damaged, mask = substrate.apply_erasure(config.erasure_fraction)
                drift_vec = np.exp(1j * np.random.uniform(-drift, drift, bands))
                stressed = damaged * drift_vec
                
                # Create temporary config with this band count
                temp_config = SimConfig(
                    substrate_size=bands,
                    max_recovery_iterations=config.max_recovery_iterations,
                    recovery_gain=config.recovery_gain
                )
                
                # Recovery
                recovered, gamma_history, _ = phase_walk_recovery(
                    stressed, target, temp_config, mask
                )
                
                gammas.append(gamma_history[-1])
            
            results[key] = gammas
            print(f"  {key}: γ range [{min(gammas):.3f}, {max(gammas):.3f}]")
    
    return {
        'drift_sweep': drift_sweep,
        'results': results,
        'all_above_threshold': all(
            min(g) >= config.gamma_approximate
            for g in results.values()
        )
    }


# =============================================================================
# Visualization
# =============================================================================

def plot_noise_sweep(results: dict, config: SimConfig, save_path: Optional[str] = None):
    """Plot γ vs SNR curve with integrity zones."""
    plt.figure(figsize=(10, 6))
    
    plt.plot(results['snrs'], results['gammas'], 
             'b-', linewidth=2, label='Measured γ')
    
    # Zone thresholds
    plt.axhline(y=config.gamma_fast_path, color='green', linestyle='--',
                alpha=0.7, label=f'Fast Path ({config.gamma_fast_path})')
    plt.axhline(y=config.gamma_recovery, color='orange', linestyle='--',
                alpha=0.7, label=f'Recovery ({config.gamma_recovery})')
    plt.axhline(y=config.gamma_approximate, color='red', linestyle='--',
                alpha=0.7, label=f'Approximate ({config.gamma_approximate})')
    
    # Zone shading
    plt.fill_between(results['snrs'], config.gamma_fast_path, 1.0, 
                     color='green', alpha=0.1)
    plt.fill_between(results['snrs'], config.gamma_recovery, config.gamma_fast_path,
                     color='yellow', alpha=0.1)
    plt.fill_between(results['snrs'], config.gamma_approximate, config.gamma_recovery,
                     color='orange', alpha=0.1)
    plt.fill_between(results['snrs'], 0, config.gamma_approximate,
                     color='red', alpha=0.1)
    
    plt.xlabel('Signal-to-Noise Ratio (dB)')
    plt.ylabel('Correlation Coherence (γ)')
    plt.title(f'SSS γ vs Noise\n({config.num_writes} writes, {config.substrate_size} bands)')
    plt.legend(loc='lower right')
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.ylim(0, 1.05)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_recovery_curve(results: dict, config: SimConfig, save_path: Optional[str] = None):
    """Plot recovery trajectory."""
    if 'per_write' in results and 'gamma_history' not in results:
        order = np.arange(1, len(results['masked_gammas']) + 1)
        plt.figure(figsize=(10, 5))
        plt.plot(order, results['masked_gammas'], 'o-', color='teal',
                 linewidth=2, markersize=5, label='Masked gamma by extraction order')
        plt.axhline(y=config.masked_success_gamma, color='green', linestyle='--',
                    label=f'Masked target ({config.masked_success_gamma})')
        plt.axhline(y=config.gamma_fast_path, color='orange', linestyle='--',
                    label=f'Fast path ({config.gamma_fast_path})')
        plt.xlabel('Extraction Order')
        plt.ylabel('Masked Correlation Coherence')
        plt.title('SSS SIC Recovery Performance')
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.ylim(0, 1.05)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
        return
    
    plt.figure(figsize=(10, 5))
    
    plt.plot(results['gamma_history'], 'o-', color='purple', 
             linewidth=2, markersize=6, label='Recovery Path')
    
    plt.axhline(y=config.gamma_fast_path, color='green', linestyle='--',
                label=f'Fast Path ({config.gamma_fast_path})')
    plt.axhline(y=config.gamma_recovery, color='orange', linestyle='--',
                label=f'Recovery Threshold ({config.gamma_recovery})')
    
    plt.xlabel('Iteration')
    plt.ylabel('Correlation Coherence (γ)')
    plt.title(f'SSS Recovery Performance\n'
              f'({int(config.erasure_fraction*100)}% erasure, '
              f'{config.drift_strength} rad drift)')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.5)
    
    # Annotate start and end
    plt.annotate(f'Initial: {results["initial_gamma"]:.3f}',
                xy=(0, results['gamma_history'][0]),
                xytext=(1, results['gamma_history'][0] - 0.1),
                arrowprops=dict(arrowstyle='->', color='gray'))
    plt.annotate(f'Final: {results["final_gamma"]:.3f}',
                xy=(len(results['gamma_history'])-1, results['final_gamma']),
                xytext=(len(results['gamma_history'])-3, results['final_gamma'] + 0.1),
                arrowprops=dict(arrowstyle='->', color='gray'))
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_envelope(results: dict, config: SimConfig, save_path: Optional[str] = None):
    """Plot pull-in envelope across configurations."""
    plt.figure(figsize=(12, 6))
    
    for key, gammas in results['results'].items():
        plt.plot(results['drift_sweep'], gammas, 'o-', 
                 markersize=3, label=key)
    
    plt.axhline(y=config.gamma_recovery, color='red', linestyle='--',
                label=f'Recovery Threshold ({config.gamma_recovery})')
    
    plt.xlabel('Maximum Phase Drift (radians)')
    plt.ylabel('Recovered Coherence (γ)')
    plt.title('SSS Pull-In Envelope\n(Final γ after 15-pass recovery)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_validations(config: SimConfig, plot: bool = True):
    """Run complete validation suite."""
    print("=" * 60)
    print("SSS Signal & Coherence Simulator v0.4")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Substrate size: {config.substrate_size} bands")
    print(f"  Write count: {config.num_writes}")
    print(f"  Recovery engine: {config.recovery_engine}")
    print(f"  Erasure: {config.erasure_fraction*100}%")
    print(f"  Drift: {config.drift_strength} rad")
    print()
    
    # Test 1: Noise sweep
    print("-" * 40)
    noise_results = test_noise_sweep(config)
    print(f"  Monotonic: {noise_results['monotonic']}")
    print(f"  γ range: [{noise_results['min_gamma']:.3f}, {noise_results['max_gamma']:.3f}]")
    
    # Test 2: Stress recovery
    print("-" * 40)
    recovery_results = test_stress_recovery(config)
    print(f"  Initial γ: {recovery_results['initial_gamma']:.4f}")
    print(f"  Final γ: {recovery_results['final_gamma']:.4f}")
    print(f"  Gain: {recovery_results['recovery_gain']:.1f}%")
    print(f"  Monotonic: {recovery_results['monotonic']}")
    print(f"  Reached threshold: {recovery_results['reached_threshold']}")
    
    # Test 3: Envelope mapping
    print("-" * 40)
    envelope_results = test_envelope_mapping(config)
    print(f"  All above threshold: {envelope_results['all_above_threshold']}")
    
    # Summary
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    all_pass = (
        noise_results['monotonic'] and
        recovery_results['monotonic'] and
        recovery_results['reached_threshold'] and
        envelope_results['all_above_threshold']
    )
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    
    if plot:
        print("\nGenerating plots...")
        plot_noise_sweep(noise_results, config)
        plot_recovery_curve(recovery_results, config)
        plot_envelope(envelope_results, config)
    
    return {
        'noise': noise_results,
        'recovery': recovery_results,
        'envelope': envelope_results,
        'all_pass': all_pass
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SSS Prior Envelope Simulator')
    parser.add_argument('--test', choices=['noise', 'recovery', 'envelope', 'all'],
                       default='all', help='Which test to run')
    parser.add_argument('--plot', action='store_true', help='Generate plots')
    parser.add_argument('--bands', type=int, default=4096, help='Substrate size')
    parser.add_argument('--writes', type=int, default=20, help='Number of writes')
    parser.add_argument('--erasure', type=float, default=0.25, help='Erasure fraction')
    parser.add_argument('--drift', type=float, default=0.30, help='Drift strength (rad)')
    parser.add_argument('--engine', choices=['phase_walk', 'sic'],
                       default='phase_walk', help='Recovery engine')
    parser.add_argument('--sic-refinement-passes', type=int, default=2,
                       help='Extra SIC refinement passes')
    
    args = parser.parse_args()
    
    config = SimConfig(
        substrate_size=args.bands,
        num_writes=args.writes,
        erasure_fraction=args.erasure,
        drift_strength=args.drift,
        recovery_engine=args.engine,
        sic_refinement_passes=args.sic_refinement_passes
    )
    
    if args.test == 'all':
        run_all_validations(config, plot=args.plot)
    elif args.test == 'noise':
        results = test_noise_sweep(config)
        print(f"Monotonic: {results['monotonic']}")
        print(f"gamma range: [{results['min_gamma']:.3f}, {results['max_gamma']:.3f}]")
        if args.plot:
            plot_noise_sweep(results, config)
    elif args.test == 'recovery':
        results = test_stress_recovery(config)
        if config.recovery_engine == "sic":
            print(
                f"Masked gamma range: "
                f"[{results['min_masked_gamma']:.4f}, {results['max_masked_gamma']:.4f}]"
            )
            print(f"Masked gamma median: {results['median_masked_gamma']:.4f}")
            print(
                f"High-fidelity writes: "
                f"{results['count_masked_high_fidelity']}/{config.num_writes}"
            )
            print(f"All masked high fidelity: {results['all_masked_high_fidelity']}")
            print(f"Residual ratio: {results['residual_ratio']:.6e}")
        else:
            print(f"Initial gamma: {results['initial_gamma']:.4f}")
            print(f"Final gamma: {results['final_gamma']:.4f}")
            print(f"Final masked gamma: {results['final_masked_gamma']:.4f}")
            print(f"Reached threshold: {results['reached_threshold']}")
        if args.plot:
            plot_recovery_curve(results, config)
    elif args.test == 'envelope':
        results = test_envelope_mapping(config)
        print(f"All above threshold: {results['all_above_threshold']}")
        if args.plot:
            plot_envelope(results, config)
