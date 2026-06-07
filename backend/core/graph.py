"""
backend/core/graph.py

Neo4j integration — push population nodes after simulation, serve graph samples.

Node types
──────────
(:Product  {name, product})
(:Segment  {name, product, share, description, price_sensitivity, …})
(:User     {uid, product, segment, status, status_label, need_level, trust_score, …})

Relationships
─────────────
(User)-[:IN_SEGMENT]->(Segment)
(Segment)-[:PART_OF]->(Product)

Graceful no-op if Neo4j is unreachable — returns {source: "unavailable"}.
"""
import math
import numpy as np
from backend.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, USE_NEO4J

_STATUS_LABELS = {0: "unaware", 1: "aware", 2: "active", 3: "churned"}
_SEGMENT_COLORS = ["#818cf8", "#34d399", "#fbbf24", "#f472b6"]

_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        try:
            _driver.verify_connectivity()
            return _driver
        except Exception:
            _driver = None

    if not USE_NEO4J:
        return None

    try:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _driver.verify_connectivity()
        return _driver
    except Exception as e:
        print(f"[graph] Neo4j unavailable: {e}")
        return None


def is_connected() -> bool:
    return _get_driver() is not None


def push_population(
    product_name: str,
    segments: list,
    pop,
    final_status: np.ndarray,
    sample_per_segment: int = 500,
) -> bool:
    """
    Encrypt population sample into Neo4j.
    Called once per simulation run; clears previous data for the same product name.
    """
    driver = _get_driver()
    if driver is None:
        return False

    rng = np.random.default_rng(42)

    try:
        with driver.session() as session:
            # Clear stale data for this product
            session.run(
                "MATCH (n) WHERE n.product = $pn DETACH DELETE n",
                pn=product_name,
            )

            # Product node
            session.run(
                "CREATE (:Product {name: $name, product: $pn})",
                name=product_name, pn=product_name,
            )

            # Segment nodes
            for i, seg in enumerate(segments):
                session.run(
                    """
                    CREATE (s:Segment {
                        name: $name, product: $pn, share: $share,
                        description: $desc,
                        price_sensitivity: $ps, need_urgency: $nu,
                        tech_affinity: $ta, competitor_loyalty: $cl,
                        social_influence: $si, color: $color, seg_idx: $idx
                    })
                    WITH s
                    MATCH (p:Product {product: $pn})
                    CREATE (s)-[:PART_OF]->(p)
                    """,
                    name=seg.segment_name, pn=product_name,
                    share=seg.share, desc=seg.description,
                    ps=seg.price_sensitivity, nu=seg.need_urgency,
                    ta=seg.tech_affinity, cl=seg.competitor_loyalty,
                    si=seg.social_influence,
                    color=_SEGMENT_COLORS[i % len(_SEGMENT_COLORS)],
                    idx=i,
                )

            # Sample users per segment, batch create
            batch: list[dict] = []
            for seg_idx, seg in enumerate(segments):
                mask = pop.segment_id == seg_idx
                indices = np.where(mask)[0]
                n_sample = min(sample_per_segment, len(indices))
                sampled = rng.choice(indices, n_sample, replace=False)

                for ui, idx in enumerate(sampled):
                    st = int(final_status[idx])
                    batch.append({
                        "uid":               f"{product_name}_s{seg_idx}_u{ui}",
                        "product":           product_name,
                        "segment":           seg.segment_name,
                        "seg_idx":           seg_idx,
                        "price_sensitivity": round(float(pop.price_sensitivity[idx]), 4),
                        "need_level":        round(float(pop.need_level[idx]), 4),
                        "trust_score":       round(float(pop.trust_score[idx]), 4),
                        "competitor_loyalty":round(float(pop.competitor_loyalty[idx]), 4),
                        "social_influence":  round(float(pop.social_influence[idx]), 4),
                        "income_monthly":    round(float(pop.income_monthly[idx]), 2),
                        "purchase_threshold":round(float(pop.purchase_threshold[idx]), 4),
                        "status":            st,
                        "status_label":      _STATUS_LABELS[st],
                    })

            # Push in one UNWIND batch
            session.run(
                """
                UNWIND $users AS u
                CREATE (n:User {
                    uid: u.uid, product: u.product,
                    segment: u.segment, seg_idx: u.seg_idx,
                    price_sensitivity: u.price_sensitivity,
                    need_level: u.need_level,
                    trust_score: u.trust_score,
                    competitor_loyalty: u.competitor_loyalty,
                    social_influence: u.social_influence,
                    income_monthly: u.income_monthly,
                    purchase_threshold: u.purchase_threshold,
                    status: u.status,
                    status_label: u.status_label
                })
                WITH n, u
                MATCH (s:Segment {name: u.segment, product: u.product})
                CREATE (n)-[:IN_SEGMENT]->(s)
                """,
                users=batch,
            )

        return True

    except Exception as e:
        print(f"[graph] push failed: {e}")
        return False


def get_graph_data(product_name: str, display_per_segment: int = 50) -> dict:
    """
    Query Neo4j and return structured data for pyvis rendering.

    Returns
    -------
    dict with keys:
        source          "neo4j" | "unavailable" | "not_found" | "error:<msg>"
        product_name    str
        segments        list[dict]  — name, share, desc, color, seg_idx
        users           list[dict]  — uid, seg, seg_idx, status, status_label, …
        stats           dict        — unaware/aware/active/churned counts
        total_stored    int
    """
    driver = _get_driver()
    if driver is None:
        return {"source": "unavailable", "segments": [], "users": [], "stats": {}}

    try:
        with driver.session() as session:
            # Segments
            segs = session.run(
                """
                MATCH (p:Product {name: $name})<-[:PART_OF]-(s:Segment)
                RETURN s.name AS seg_name, s.share AS share, s.description AS desc,
                       s.price_sensitivity AS ps, s.tech_affinity AS ta,
                       s.color AS color, s.seg_idx AS seg_idx
                ORDER BY s.seg_idx
                """,
                name=product_name,
            ).data()

            if not segs:
                return {"source": "not_found", "segments": [], "users": [], "stats": {}}

            # Users (random sample per display_per_segment)
            users = session.run(
                """
                MATCH (u:User {product: $name})-[:IN_SEGMENT]->(s:Segment)
                WITH u, s.name AS seg, s.seg_idx AS seg_idx, rand() AS r
                ORDER BY seg_idx, r
                WITH seg_idx, collect({
                    uid:               u.uid,
                    seg:               seg,
                    seg_idx:           seg_idx,
                    status:            u.status,
                    status_label:      u.status_label,
                    trust_score:       u.trust_score,
                    need_level:        u.need_level,
                    income_monthly:    u.income_monthly,
                    purchase_threshold:u.purchase_threshold
                })[..$limit] AS sample
                UNWIND sample AS row
                RETURN row
                """,
                name=product_name, limit=display_per_segment,
            ).data()
            users = [r["row"] for r in users]

            # Status stats across all stored nodes
            stats_raw = session.run(
                """
                MATCH (u:User {product: $name})
                RETURN u.status_label AS label, count(*) AS cnt
                """,
                name=product_name,
            ).data()
            stats = {r["label"]: r["cnt"] for r in stats_raw}

            total_stored = session.run(
                "MATCH (u:User {product: $name}) RETURN count(u) AS n",
                name=product_name,
            ).single()["n"]

        return {
            "source":       "neo4j",
            "product_name": product_name,
            "segments":     segs,
            "users":        users,
            "stats":        stats,
            "total_stored": total_stored,
        }

    except Exception as e:
        return {"source": f"error: {e}", "segments": [], "users": [], "stats": {}}
