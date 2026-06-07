"""
Monte Carlo runner: vary key assumptions → P10/P50/P90 confidence envelopes.
"""
import numpy as np
from backend.core.models import (
    CustomerSegment, MonthlyMetrics, SimulationConfig, SegmentAdoption
)
from backend.engines.simulation import (
    Population, ProductParams, run_simulation, compute_segment_adoption
)


def _vary_params(params: ProductParams, rng: np.random.Generator) -> ProductParams:
    def jitter(v: float, lo: float, hi: float, lo_clip: float = 0.0, hi_clip: float = 1.0) -> float:
        return float(np.clip(v * rng.uniform(lo, hi), lo_clip, hi_clip))

    return ProductParams(
        monthly_price=params.monthly_price,
        feature_match=jitter(params.feature_match, 0.80, 1.20),
        switching_cost=jitter(params.switching_cost, 0.85, 1.15),
        brand_recognition=jitter(params.brand_recognition, 0.70, 1.30),
        virality_coefficient=float(np.clip(params.virality_coefficient * rng.uniform(0.60, 1.40), 0, 2)),
        monthly_marketing_reach=float(np.clip(params.monthly_marketing_reach * rng.uniform(0.60, 1.40), 0.001, 0.15)),
        churn_rate_monthly=float(np.clip(params.churn_rate_monthly * rng.uniform(0.70, 1.30), 0.005, 0.35)),
        billing_model=params.billing_model,
    )


def _percentile_series(all_runs: list[list[MonthlyMetrics]], p: float) -> list[MonthlyMetrics]:
    n_months = len(all_runs[0])
    result = []
    for m in range(n_months):
        month_runs = [r[m] for r in all_runs]
        result.append(MonthlyMetrics(
            month=m + 1,
            mrr=round(float(np.percentile([r.mrr for r in month_runs], p)), 2),
            total_customers=int(np.percentile([r.total_customers for r in month_runs], p)),
            new_customers=int(np.percentile([r.new_customers for r in month_runs], p)),
            churned_customers=int(np.percentile([r.churned_customers for r in month_runs], p)),
            cumulative_revenue=round(float(np.percentile([r.cumulative_revenue for r in month_runs], p)), 2),
            churn_rate=round(float(np.percentile([r.churn_rate for r in month_runs], p)), 4),
            adoption_rate=round(float(np.percentile([r.adoption_rate for r in month_runs], p)), 4),
        ))
    return result


def run_monte_carlo(
    pop: Population,
    base_params: ProductParams,
    config: SimulationConfig,
    segments: list[CustomerSegment],
) -> dict:
    """
    Returns dict with keys: base_monthly, mc_p10, mc_p50, mc_p90, segment_adoption.
    """
    master_rng = np.random.default_rng(config.random_seed + 9999)

    # Deterministic base run
    base_monthly, base_status = run_simulation(pop, base_params, seed=config.random_seed, n_months=config.n_months)

    # MC runs
    all_runs: list[list[MonthlyMetrics]] = []
    for i in range(config.n_monte_carlo):
        varied = _vary_params(base_params, master_rng)
        monthly, _ = run_simulation(pop, varied, seed=config.random_seed + i + 1, n_months=config.n_months)
        all_runs.append(monthly)

    seg_raw = compute_segment_adoption(pop, segments, base_status)
    segment_adoption = [SegmentAdoption(**r) for r in seg_raw]

    return {
        "base_monthly":     base_monthly,
        "base_status":      base_status,   # final np.ndarray — used by Neo4j push
        "mc_p10":           _percentile_series(all_runs, 10),
        "mc_p50":           _percentile_series(all_runs, 50),
        "mc_p90":           _percentile_series(all_runs, 90),
        "segment_adoption": segment_adoption,
    }
