import os
import pytest
from scripts.simulate_flows import run_full_simulation

@pytest.mark.performance
def test_stress_avg_duration_sla():
    # REAL_ONLY mode avoids mock uniqueness
    metrics = run_full_simulation(stress_iterations=5, stress_unique_names=False)
    avg = metrics.get('stress_summary', {}).get('avg_duration')
    assert avg is not None
    # SLA: average duration under 0.3s
    assert avg < 0.3, f"Avg stress duration {avg:.4f}s exceeds SLA (<0.3s)"

@pytest.mark.performance
def test_memory_delta_reasonable():
    metrics = run_full_simulation(stress_iterations=3, stress_unique_names=False)
    ss = metrics.get('stress_summary', {})
    delta = ss.get('memory_rss_delta')
    # Allow None if psutil unavailable
    if delta is not None:
        # Arbitrary upper bound (50MB) for delta per short run
        assert delta < 50 * 1024 * 1024, f"Memory delta {delta} too high"
