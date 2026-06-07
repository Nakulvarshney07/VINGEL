from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    product_name: str
    product_description: str
    target_market: str
    price: float
    billing_model: str  # monthly_subscription | annual_subscription | one_time | freemium
    geography: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)


class BusinessAssumptions(BaseModel):
    total_addressable_market: int
    problem_severity: float
    feature_match: float
    switching_cost: float
    brand_recognition: float
    virality_coefficient: float
    monthly_marketing_reach: float
    churn_rate_monthly: float


class CustomerSegment(BaseModel):
    segment_name: str
    share: float
    description: str = ""
    age_min: int = 18
    age_max: int = 65
    income_monthly_min: float = 2000.0
    income_monthly_max: float = 8000.0
    price_sensitivity: float
    need_urgency: float
    trust_threshold: float
    tech_affinity: float
    competitor_loyalty: float
    social_influence: float


class SimulationConfig(BaseModel):
    n_users: int = 100_000
    n_months: int = 24
    n_monte_carlo: int = 100
    random_seed: int = 42


class MonthlyMetrics(BaseModel):
    month: int
    new_customers: int
    total_customers: int
    churned_customers: int
    mrr: float
    cumulative_revenue: float
    churn_rate: float
    adoption_rate: float


class SegmentAdoption(BaseModel):
    segment_name: str
    adoption_rate: float
    total_customers: int


class MonteCarloResult(BaseModel):
    base_monthly: list[MonthlyMetrics]
    mc_p10: list[MonthlyMetrics]
    mc_p50: list[MonthlyMetrics]
    mc_p90: list[MonthlyMetrics]
    segment_adoption: list[SegmentAdoption]


class SimulationResult(BaseModel):
    product_name: str
    assumptions: BusinessAssumptions
    segments: list[CustomerSegment]
    base_monthly: list[MonthlyMetrics]
    mc_p10: list[MonthlyMetrics]
    mc_p50: list[MonthlyMetrics]
    mc_p90: list[MonthlyMetrics]
    segment_adoption: list[SegmentAdoption]
    final_mrr: float
    final_arr: float
    peak_adoption_rate: float
    final_churn_rate: float


class SimulateRequest(BaseModel):
    product: ProductInput
    config: SimulationConfig = Field(default_factory=SimulationConfig)
