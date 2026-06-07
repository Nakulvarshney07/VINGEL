"""
Core simulation engine: vectorized NumPy population + monthly funnel loop.
"""
import numpy as np
from dataclasses import dataclass
from backend.core.models import (
    ProductInput, BusinessAssumptions, CustomerSegment, MonthlyMetrics
)


@dataclass
class Population:
    """Immutable population arrays. Shape: (n_users,)"""
    segment_id: np.ndarray
    price_sensitivity: np.ndarray
    need_level: np.ndarray
    trust_score: np.ndarray
    competitor_loyalty: np.ndarray
    social_influence: np.ndarray
    income_monthly: np.ndarray
    purchase_threshold: np.ndarray
    churn_threshold: np.ndarray
    n: int


@dataclass
class ProductParams:
    monthly_price: float
    feature_match: float
    switching_cost: float
    brand_recognition: float
    virality_coefficient: float
    monthly_marketing_reach: float
    churn_rate_monthly: float
    billing_model: str


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def build_product_params(
    product: ProductInput,
    assumptions: BusinessAssumptions,
) -> ProductParams:
    price = product.price
    if product.billing_model == "annual_subscription":
        monthly_price = price / 12.0
    else:
        monthly_price = price

    return ProductParams(
        monthly_price=monthly_price,
        feature_match=assumptions.feature_match,
        switching_cost=assumptions.switching_cost,
        brand_recognition=assumptions.brand_recognition,
        virality_coefficient=assumptions.virality_coefficient,
        monthly_marketing_reach=assumptions.monthly_marketing_reach,
        churn_rate_monthly=assumptions.churn_rate_monthly,
        billing_model=product.billing_model,
    )


def generate_population(
    segments: list[CustomerSegment],
    n_users: int,
    seed: int = 42,
) -> Population:
    rng = np.random.default_rng(seed)

    segment_id = np.empty(n_users, dtype=np.int32)
    price_sensitivity = np.empty(n_users)
    need_level = np.empty(n_users)
    trust_score = np.empty(n_users)
    competitor_loyalty = np.empty(n_users)
    social_influence = np.empty(n_users)
    income_monthly = np.empty(n_users)

    cursor = 0
    for idx, seg in enumerate(segments):
        n_seg = int(n_users * seg.share) if idx < len(segments) - 1 else n_users - cursor
        end = cursor + n_seg

        segment_id[cursor:end] = idx

        def _sample(mean: float, n: int = n_seg, std: float = 0.12) -> np.ndarray:
            return np.clip(rng.normal(mean, std, n), 0.0, 1.0)

        price_sensitivity[cursor:end] = _sample(seg.price_sensitivity)
        need_level[cursor:end] = _sample(seg.need_urgency)
        # high trust_threshold ↔ low initial trust score
        trust_score[cursor:end] = _sample(1.0 - seg.trust_threshold)
        competitor_loyalty[cursor:end] = _sample(seg.competitor_loyalty)
        social_influence[cursor:end] = _sample(seg.social_influence)

        inc_mean = (seg.income_monthly_min + seg.income_monthly_max) / 2
        inc_std = (seg.income_monthly_max - seg.income_monthly_min) / 4
        income_monthly[cursor:end] = np.clip(rng.normal(inc_mean, inc_std, n_seg), 500, 1e6)

        cursor = end

    purchase_threshold = rng.beta(2.5, 2.5, n_users)
    churn_threshold = rng.beta(4.0, 2.0, n_users)

    return Population(
        segment_id=segment_id,
        price_sensitivity=price_sensitivity,
        need_level=need_level,
        trust_score=trust_score,
        competitor_loyalty=competitor_loyalty,
        social_influence=social_influence,
        income_monthly=income_monthly,
        purchase_threshold=purchase_threshold,
        churn_threshold=churn_threshold,
        n=n_users,
    )


def _conversion_scores(
    pop: Population,
    mask: np.ndarray,
    params: ProductParams,
    brand_t: float,
    adoption_rate: float,
) -> np.ndarray:
    ps = pop.price_sensitivity[mask]
    nl = pop.need_level[mask]
    ts = pop.trust_score[mask]
    cl = pop.competitor_loyalty[mask]
    si = pop.social_influence[mask]
    inc = pop.income_monthly[mask]

    fm = params.feature_match
    sc = params.switching_cost

    need_fit = nl * fm
    price_fraction = params.monthly_price / np.maximum(inc, 1.0)
    affordability = np.clip(1.0 - np.maximum(0.0, price_fraction - 0.05) * ps * 8.0, 0.0, 1.0)
    trust = ts * brand_t
    peer_influence = si * adoption_rate
    brand_score = brand_t * 0.8 + 0.2 * ts
    perceived_risk = (1.0 - ts) * (1.0 - fm) * 0.5

    raw = (
        0.30 * need_fit
        + 0.20 * fm
        + 0.15 * trust
        + 0.10 * peer_influence
        + 0.10 * brand_score
        + 0.15 * affordability
        - 0.20 * cl
        - 0.15 * sc
        - 0.10 * perceived_risk
    )
    return _sigmoid(4.0 * raw - 3.0)


def _churn_probs(
    pop: Population,
    mask: np.ndarray,
    params: ProductParams,
    brand_t: float,
) -> np.ndarray:
    ps = pop.price_sensitivity[mask]
    cl = pop.competitor_loyalty[mask]
    inc = pop.income_monthly[mask]

    price_fraction = params.monthly_price / np.maximum(inc, 1.0)
    affordability = np.clip(1.0 - np.maximum(0.0, price_fraction - 0.05) * ps * 8.0, 0.0, 1.0)
    adjusted = params.churn_rate_monthly * (1.0 - 0.5 * affordability + 0.3 * cl) * (1.0 - 0.1 * brand_t)
    return np.clip(adjusted, 0.005, 0.40)


def _mrr_for_month(params: ProductParams, new_customers: int, total_customers: int) -> float:
    if params.billing_model == "one_time":
        return float(new_customers * params.monthly_price)
    elif params.billing_model == "freemium":
        return float(total_customers * params.monthly_price * 0.05)
    return float(total_customers * params.monthly_price)


def run_simulation(
    pop: Population,
    params: ProductParams,
    seed: int = 0,
    n_months: int = 24,
) -> tuple[list[MonthlyMetrics], np.ndarray]:
    """
    Run a single simulation. Returns (monthly_metrics, final_status_array).
    Status: 0=unaware, 1=aware, 2=active, 3=churned.
    """
    rng = np.random.default_rng(seed)
    status = np.zeros(pop.n, dtype=np.int8)

    initial_aware = rng.random(pop.n) < 0.01
    status[initial_aware] = 1

    cumulative_revenue = 0.0
    metrics: list[MonthlyMetrics] = []

    for month in range(1, n_months + 1):
        brand_t = float(np.clip(params.brand_recognition + 0.012 * (month - 1), 0, 1))
        active_count = int(np.sum(status == 2))
        adoption_rate = active_count / pop.n

        # Awareness
        unaware_mask = status == 0
        n_unaware = int(unaware_mask.sum())
        if n_unaware > 0:
            wom_rate = adoption_rate * params.virality_coefficient * pop.social_influence[unaware_mask]
            total_aware_prob = np.clip(params.monthly_marketing_reach + wom_rate, 0, 0.8)
            fires = rng.random(n_unaware) < total_aware_prob
            new_aware = unaware_mask.copy()
            new_aware[unaware_mask] = fires
            status[new_aware] = 1

        # Conversion
        aware_mask = status == 1
        n_aware = int(aware_mask.sum())
        new_count = 0
        if n_aware > 0:
            conv_probs = _conversion_scores(pop, aware_mask, params, brand_t, adoption_rate)
            fires = conv_probs > pop.purchase_threshold[aware_mask]
            converts = aware_mask.copy()
            converts[aware_mask] = fires
            status[converts] = 2
            new_count = int(fires.sum())

        # Churn
        active_mask = status == 2
        n_active = int(active_mask.sum())
        churned_count = 0
        if n_active > 0:
            churn_p = _churn_probs(pop, active_mask, params, brand_t)
            fires = rng.random(n_active) < churn_p
            churns = active_mask.copy()
            churns[active_mask] = fires
            status[churns] = 3
            churned_count = int(fires.sum())

        total_active = int(np.sum(status == 2))
        mrr = _mrr_for_month(params, new_count, total_active)
        cumulative_revenue += mrr

        metrics.append(MonthlyMetrics(
            month=month,
            new_customers=new_count,
            total_customers=total_active,
            churned_customers=churned_count,
            mrr=round(mrr, 2),
            cumulative_revenue=round(cumulative_revenue, 2),
            churn_rate=round(churned_count / max(active_count, 1), 4),
            adoption_rate=round(total_active / pop.n, 4),
        ))

    return metrics, status.copy()


def compute_segment_adoption(
    pop: Population,
    segments: list[CustomerSegment],
    final_status: np.ndarray,
) -> list[dict]:
    results = []
    cursor = 0
    for idx, seg in enumerate(segments):
        n_seg = int(pop.n * seg.share) if idx < len(segments) - 1 else pop.n - cursor
        end = cursor + n_seg
        seg_status = final_status[cursor:end]
        n_converted = int(np.sum(seg_status == 2))
        results.append({
            "segment_name": seg.segment_name,
            "adoption_rate": round(n_converted / max(n_seg, 1), 4),
            "total_customers": n_converted,
        })
        cursor = end
    return results
