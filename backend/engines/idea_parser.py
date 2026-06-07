"""
idea_parser.py
Uses Sarvam AI to parse a product idea into business simulation assumptions.
Falls back to smart heuristics if no API key is set.
"""
import json
import re
from backend.core.models import ProductInput, BusinessAssumptions
from backend.core.config import USE_SARVAM, SARVAM_API_KEY, SARVAM_MODEL, SARVAM_BASE_URL


_PROMPT = """You are a senior market research analyst. Analyze this product and return
realistic business simulation assumptions as a JSON object.

Product Name:    {product_name}
Description:     {product_description}
Target Market:   {target_market}
Price:           ${price} ({billing_model})
Geography:       {geography}
Competitors:     {competitors}
Channels:        {channels}
Key Features:    {features}

Return ONLY a valid JSON object with exactly these fields:

{{
  "total_addressable_market": <integer — realistic number of potential users/businesses>,
  "problem_severity": <float 0.0-1.0 — how urgent/painful is the problem>,
  "feature_match": <float 0.0-1.0 — how well features solve the core need>,
  "switching_cost": <float 0.0-1.0 — friction to leave existing tools>,
  "brand_recognition": <float 0.02-0.25 — initial awareness for a new entrant>,
  "virality_coefficient": <float 0.0-2.0 — word-of-mouth growth factor>,
  "monthly_marketing_reach": <float 0.005-0.06 — fraction of TAM reached per month>,
  "churn_rate_monthly": <float 0.01-0.15 — monthly customer churn rate>
}}

Be conservative and realistic. A brand new product has very low brand_recognition.
No markdown, no explanation — raw JSON only."""


def _heuristic_fallback(product: ProductInput) -> BusinessAssumptions:
    price = product.price
    billing = product.billing_model
    n_comp = len(product.competitors)
    n_feat = len(product.features)
    n_chan = len(product.channels)

    if billing == "freemium":        tam = 2_000_000
    elif price < 20:                 tam = 1_000_000
    elif price < 100:                tam = 300_000
    elif price < 500:                tam = 80_000
    else:                            tam = 20_000

    problem_severity = min(0.90, 0.50 + n_feat * 0.04)
    feature_match    = min(0.90, 0.55 + n_feat * 0.03)

    if n_comp == 0:    switching_cost, brand = 0.15, 0.05
    elif n_comp <= 2:  switching_cost, brand = 0.35, 0.08
    elif n_comp <= 4:  switching_cost, brand = 0.50, 0.06
    else:              switching_cost, brand = 0.65, 0.04

    virality     = 1.10 if billing == "freemium" else (0.65 if price < 50 else 0.40)
    mktg_reach   = min(0.06, 0.015 + n_chan * 0.005)
    churn        = 0.00 if billing == "one_time" else (0.09 if billing == "freemium" else
                   0.025 if price > 200 else 0.04 if price > 50 else 0.06)

    return BusinessAssumptions(
        total_addressable_market=tam,
        problem_severity=round(problem_severity, 2),
        feature_match=round(feature_match, 2),
        switching_cost=round(switching_cost, 2),
        brand_recognition=round(brand, 2),
        virality_coefficient=round(virality, 2),
        monthly_marketing_reach=round(mktg_reach, 3),
        churn_rate_monthly=round(churn, 3),
    )


def parse_idea(product: ProductInput) -> tuple[BusinessAssumptions, bool]:
    """Returns (BusinessAssumptions, used_sarvam: bool)."""
    if not USE_SARVAM:
        return _heuristic_fallback(product), False

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=SARVAM_API_KEY,
            base_url=SARVAM_BASE_URL,
        )

        prompt = _PROMPT.format(
            product_name=product.product_name,
            product_description=product.product_description,
            target_market=product.target_market,
            price=product.price,
            billing_model=product.billing_model,
            geography=", ".join(product.geography) or "Global",
            competitors=", ".join(product.competitors) or "None listed",
            channels=", ".join(product.channels) or "Not specified",
            features=", ".join(product.features) or "Not specified",
        )

        response = client.chat.completions.create(
            model=SARVAM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$",    "", text)

        data = json.loads(text)
        return BusinessAssumptions(**data), True

    except Exception:
        return _heuristic_fallback(product), False
