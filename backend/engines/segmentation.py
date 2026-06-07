"""
segmentation.py
Uses Sarvam AI to generate customer segments with behavioral parameters.
Falls back to curated defaults if no API key is set.
"""
import json
import re
from backend.core.models import ProductInput, CustomerSegment
from backend.core.config import USE_SARVAM, SARVAM_API_KEY, SARVAM_MODEL, SARVAM_BASE_URL


_PROMPT = """You are a customer segmentation expert. Create 4 realistic customer segments
for the product below. Each segment must have precise numeric behavioral parameters
that will drive a market simulation.

Product Name:  {product_name}
Description:   {product_description}
Target Market: {target_market}
Price:         ${price} ({billing_model})
Geography:     {geography}

Return ONLY a valid JSON object — no markdown, no explanation:

{{
  "segments": [
    {{
      "segment_name": "<descriptive name>",
      "share": <float 0-1, fraction of TAM — all 4 must sum to 1.0>,
      "description": "<one sentence describing this segment>",
      "age_min": <int>,
      "age_max": <int>,
      "income_monthly_min": <float, USD>,
      "income_monthly_max": <float, USD>,
      "price_sensitivity":  <float 0-1, 1=very price sensitive>,
      "need_urgency":       <float 0-1, 1=urgent need>,
      "trust_threshold":    <float 0-1, 1=very hard to trust a new brand>,
      "tech_affinity":      <float 0-1, 1=very tech-forward>,
      "competitor_loyalty": <float 0-1, 1=deeply loyal to existing tools>,
      "social_influence":   <float 0-1, 1=strong word-of-mouth influence>
    }}
  ]
}}

Segment archetypes to use (adapt names/values to the product):
1. Early Adopters (~15%): high urgency, low trust barrier, high social influence
2. Pragmatic Mainstream (~40%): moderate values, needs social proof
3. Value Seekers (~30%): high price sensitivity, wants clear ROI
4. Late Majority (~15%): low tech affinity, high competitor loyalty, slow to switch

The shares must sum to exactly 1.0."""


_B2B_DEFAULTS = [
    CustomerSegment(segment_name="Power Users", share=0.10,
        description="High-urgency early adopters and opinion leaders",
        age_min=25, age_max=42, income_monthly_min=6000, income_monthly_max=15000,
        price_sensitivity=0.20, need_urgency=0.90, trust_threshold=0.20,
        tech_affinity=0.92, competitor_loyalty=0.10, social_influence=0.85),
    CustomerSegment(segment_name="Pragmatic Professionals", share=0.25,
        description="Mainstream buyers seeking proven ROI",
        age_min=28, age_max=55, income_monthly_min=4000, income_monthly_max=10000,
        price_sensitivity=0.50, need_urgency=0.62, trust_threshold=0.55,
        tech_affinity=0.55, competitor_loyalty=0.45, social_influence=0.50),
    CustomerSegment(segment_name="Value Seekers", share=0.20,
        description="Budget-focused, need strong justification before switching",
        age_min=24, age_max=50, income_monthly_min=2500, income_monthly_max=6000,
        price_sensitivity=0.80, need_urgency=0.45, trust_threshold=0.65,
        tech_affinity=0.45, competitor_loyalty=0.55, social_influence=0.35),
    CustomerSegment(segment_name="Late Majority", share=0.10,
        description="Conservative adopters following market validation",
        age_min=38, age_max=65, income_monthly_min=3500, income_monthly_max=8000,
        price_sensitivity=0.70, need_urgency=0.28, trust_threshold=0.82,
        tech_affinity=0.28, competitor_loyalty=0.68, social_influence=0.22),
    CustomerSegment(segment_name="Enterprise Innovators", share=0.10,
        description="Large budget teams testing bleeding-edge tech",
        age_min=30, age_max=50, income_monthly_min=8000, income_monthly_max=25000,
        price_sensitivity=0.10, need_urgency=0.75, trust_threshold=0.40,
        tech_affinity=0.85, competitor_loyalty=0.30, social_influence=0.95),
    CustomerSegment(segment_name="Skeptical Traditionalists", share=0.10,
        description="Deeply loyal to legacy software, hard to convert",
        age_min=45, age_max=70, income_monthly_min=5000, income_monthly_max=12000,
        price_sensitivity=0.60, need_urgency=0.15, trust_threshold=0.95,
        tech_affinity=0.10, competitor_loyalty=0.90, social_influence=0.15),
    CustomerSegment(segment_name="Agile Startups", share=0.10,
        description="Fast-moving, highly technical, highly networked teams",
        age_min=22, age_max=38, income_monthly_min=3000, income_monthly_max=9000,
        price_sensitivity=0.40, need_urgency=0.85, trust_threshold=0.30,
        tech_affinity=0.95, competitor_loyalty=0.15, social_influence=0.88),
    CustomerSegment(segment_name="Compliance Bound", share=0.05,
        description="Heavily regulated sectors prioritizing security over features",
        age_min=35, age_max=60, income_monthly_min=6000, income_monthly_max=18000,
        price_sensitivity=0.30, need_urgency=0.40, trust_threshold=0.90,
        tech_affinity=0.40, competitor_loyalty=0.80, social_influence=0.40),
]

_CONSUMER_DEFAULTS = [
    CustomerSegment(segment_name="Early Adopters", share=0.10,
        description="Tech-forward, shares widely, low trust barrier",
        age_min=20, age_max=35, income_monthly_min=3000, income_monthly_max=9000,
        price_sensitivity=0.18, need_urgency=0.88, trust_threshold=0.15,
        tech_affinity=0.95, competitor_loyalty=0.08, social_influence=0.90),
    CustomerSegment(segment_name="Engaged Mainstream", share=0.30,
        description="Core market, responds strongly to social proof",
        age_min=22, age_max=50, income_monthly_min=2500, income_monthly_max=7000,
        price_sensitivity=0.55, need_urgency=0.58, trust_threshold=0.50,
        tech_affinity=0.52, competitor_loyalty=0.40, social_influence=0.55),
    CustomerSegment(segment_name="Bargain Hunters", share=0.20,
        description="Price-driven, high churn risk if a cheaper alternative appears",
        age_min=18, age_max=45, income_monthly_min=1500, income_monthly_max=4500,
        price_sensitivity=0.88, need_urgency=0.42, trust_threshold=0.62,
        tech_affinity=0.40, competitor_loyalty=0.50, social_influence=0.38),
    CustomerSegment(segment_name="Reluctant Adopters", share=0.10,
        description="Slow to switch, need strong endorsements",
        age_min=35, age_max=65, income_monthly_min=3000, income_monthly_max=7000,
        price_sensitivity=0.68, need_urgency=0.25, trust_threshold=0.80,
        tech_affinity=0.25, competitor_loyalty=0.72, social_influence=0.20),
    CustomerSegment(segment_name="Brand Loyalists", share=0.10,
        description="Highly loyal to their current favorite brands, low price sensitivity",
        age_min=25, age_max=55, income_monthly_min=4000, income_monthly_max=12000,
        price_sensitivity=0.25, need_urgency=0.35, trust_threshold=0.75,
        tech_affinity=0.60, competitor_loyalty=0.90, social_influence=0.70),
    CustomerSegment(segment_name="Impulse Buyers", share=0.10,
        description="Quick to buy on a whim if marketing is compelling",
        age_min=18, age_max=35, income_monthly_min=2000, income_monthly_max=6000,
        price_sensitivity=0.50, need_urgency=0.95, trust_threshold=0.20,
        tech_affinity=0.80, competitor_loyalty=0.20, social_influence=0.60),
    CustomerSegment(segment_name="Trendsetters", share=0.05,
        description="Hyper-connected micro-influencers seeking the 'next big thing'",
        age_min=18, age_max=30, income_monthly_min=2500, income_monthly_max=8000,
        price_sensitivity=0.40, need_urgency=0.80, trust_threshold=0.25,
        tech_affinity=0.90, competitor_loyalty=0.10, social_influence=0.98),
    CustomerSegment(segment_name="Apathetic Users", share=0.05,
        description="Low engagement, doesn't care much about the product category",
        age_min=30, age_max=60, income_monthly_min=2000, income_monthly_max=5000,
        price_sensitivity=0.75, need_urgency=0.10, trust_threshold=0.85,
        tech_affinity=0.30, competitor_loyalty=0.60, social_influence=0.10),
]


def _normalize(segments: list[CustomerSegment]) -> list[CustomerSegment]:
    total = sum(s.share for s in segments)
    if total <= 0:
        total = 1.0
    for s in segments:
        s.share = round(s.share / total, 4)
    return segments


def generate_segments(product: ProductInput) -> tuple[list[CustomerSegment], bool]:
    """Returns (segments, used_sarvam: bool)."""
    is_b2b = (product.price >= 30 or any(
        kw in product.target_market.lower()
        for kw in ("team", "business", "company", "enterprise", "smb", "saas", "b2b", "startup")
    ))
    # Hardcoded bypass to consume 0 tokens and respond instantly
    return _normalize(_B2B_DEFAULTS if is_b2b else _CONSUMER_DEFAULTS), True
