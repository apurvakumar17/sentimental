import pytest
from sqlalchemy.orm import Session

from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.review_import_metadata import ReviewImportMetadata
from backend.app.models.absa import ReviewPrediction, ReviewAnnotation
from backend.app.schemas.recommendation import RecommendationRequest
from backend.app.services.recommendation_service import recommendation_engine


@pytest.fixture
def recommendation_fixtures(db_session: Session):
    """
    Creates deterministic test fixture with 3 smartphones of varying prices and aspect profiles:
    - Phone A (Brand Alpha, $400): Strong in Camera, weak in Battery
    - Phone B (Brand Beta, $500): Strong in Battery, moderate in Camera
    - Phone C (Brand Alpha, $900): Out of budget for sub-$600, strong in Performance
    """
    p_a = Product(name="Alpha Cam 1", brand="Alpha", canonical_url="https://example.com/alpha1")
    p_b = Product(name="Beta Power 2", brand="Beta", canonical_url="https://example.com/beta2")
    p_c = Product(name="Alpha Ultra 3", brand="Alpha", canonical_url="https://example.com/alpha3")
    db_session.add_all([p_a, p_b, p_c])
    db_session.commit()

    # Create reviews and pricing metadata
    # Phone A: $400
    r_a1 = Review(product_id=p_a.id, raw_review_text="Amazing camera", content_hash="hash_a1", rating=4.5)
    r_a2 = Review(product_id=p_a.id, raw_review_text="Terrible battery life", content_hash="hash_a2", rating=3.0)
    db_session.add_all([r_a1, r_a2])
    db_session.commit()

    m_a1 = ReviewImportMetadata(review_id=r_a1.id, price_usd=400.0, currency="USD")
    m_a2 = ReviewImportMetadata(review_id=r_a2.id, price_usd=400.0, currency="USD")
    db_session.add_all([m_a1, m_a2])

    # Phone B: $500
    r_b1 = Review(product_id=p_b.id, raw_review_text="Best battery backup", content_hash="hash_b1", rating=5.0)
    r_b2 = Review(product_id=p_b.id, raw_review_text="Decent camera", content_hash="hash_b2", rating=4.0)
    db_session.add_all([r_b1, r_b2])
    db_session.commit()

    m_b1 = ReviewImportMetadata(review_id=r_b1.id, price_usd=500.0, currency="USD")
    m_b2 = ReviewImportMetadata(review_id=r_b2.id, price_usd=500.0, currency="USD")
    db_session.add_all([m_b1, m_b2])

    # Phone C: $900
    r_c1 = Review(product_id=p_c.id, raw_review_text="Flagship processor", content_hash="hash_c1", rating=5.0)
    db_session.add(r_c1)
    db_session.commit()

    m_c1 = ReviewImportMetadata(review_id=r_c1.id, price_usd=900.0, currency="USD")
    db_session.add(m_c1)

    # Predictions for Phone A:
    # Camera -> Positive (conf=0.9), Battery -> Negative (conf=0.85)
    pred_a_cam = ReviewPrediction(review_id=r_a1.id, aspect="Camera", sentiment="Positive", confidence=0.9)
    pred_a_bat = ReviewPrediction(review_id=r_a2.id, aspect="Battery", sentiment="Negative", confidence=0.85)

    # Predictions for Phone B:
    # Battery -> Positive (conf=0.95), Camera -> Neutral (conf=0.7)
    pred_b_bat = ReviewPrediction(review_id=r_b1.id, aspect="Battery", sentiment="Positive", confidence=0.95)
    pred_b_cam = ReviewPrediction(review_id=r_b2.id, aspect="Camera", sentiment="Neutral", confidence=0.7)

    # Predictions for Phone C:
    # Performance -> Positive (conf=0.95)
    pred_c_perf = ReviewPrediction(review_id=r_c1.id, aspect="Performance", sentiment="Positive", confidence=0.95)

    db_session.add_all([pred_a_cam, pred_a_bat, pred_b_bat, pred_b_cam, pred_c_perf])
    db_session.commit()

    return {
        "p_a": p_a,
        "p_b": p_b,
        "p_c": p_c,
        "r_a1": r_a1,
        "r_a2": r_a2,
        "r_b1": r_b1,
    }


def test_aspect_definitions_endpoint(client):
    """Verify supported aspect categories and metadata endpoint."""
    resp = client.get("/api/v1/recommendations/aspects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    aspect_names = [item["aspect"] for item in data]
    assert "Battery" in aspect_names
    assert "Camera" in aspect_names
    assert "Performance" in aspect_names
    assert "Design" in aspect_names
    assert "Display" in aspect_names


def test_budget_filtering(client, recommendation_fixtures):
    """Verify budget min and max price filtering."""
    # Budget $300 - $600 should include Phone A ($400) and Phone B ($500), but exclude Phone C ($900)
    req = {
        "min_price": 300.0,
        "max_price": 600.0,
        "priorities": ["Camera", "Battery"],
    }
    resp = client.post("/api/v1/recommendations", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_products_count"] == 2
    matched_ids = [r["product_id"] for r in data["recommendations"]]
    assert recommendation_fixtures["p_a"].id in matched_ids
    assert recommendation_fixtures["p_b"].id in matched_ids
    assert recommendation_fixtures["p_c"].id not in matched_ids


def test_brand_filtering(client, recommendation_fixtures):
    """Verify filtering by preferred smartphone brands."""
    req = {
        "brands": ["Beta"],
        "priorities": ["Battery"],
    }
    resp = client.post("/api/v1/recommendations", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_products_count"] == 1
    assert data["recommendations"][0]["brand"] == "Beta"
    assert data["recommendations"][0]["product_id"] == recommendation_fixtures["p_b"].id


def test_aspect_priority_weighting_ranking(client, recommendation_fixtures):
    """
    Verify ranking order changes based on user priority:
    - If Camera is top priority, Phone A (strong Camera) should rank #1.
    - If Battery is top priority, Phone B (strong Battery) should rank #1.
    """
    # 1. Camera as Priority 1
    req_cam = {
        "min_price": 300.0,
        "max_price": 600.0,
        "priorities": ["Camera", "Battery"],
    }
    resp_cam = client.post("/api/v1/recommendations", json=req_cam)
    data_cam = resp_cam.json()
    assert data_cam["recommendations"][0]["product_id"] == recommendation_fixtures["p_a"].id
    assert data_cam["recommendations"][0]["rank"] == 1

    # 2. Battery as Priority 1
    req_bat = {
        "min_price": 300.0,
        "max_price": 600.0,
        "priorities": ["Battery", "Camera"],
    }
    resp_bat = client.post("/api/v1/recommendations", json=req_bat)
    data_bat = resp_bat.json()
    assert data_bat["recommendations"][0]["product_id"] == recommendation_fixtures["p_b"].id
    assert data_bat["recommendations"][0]["rank"] == 1


def test_empty_recommendation_results(client, recommendation_fixtures):
    """Verify clean empty state when no products match tight budget or brand filters."""
    req = {
        "min_price": 10.0,
        "max_price": 50.0,  # No phones in this price range
        "priorities": ["Camera"],
    }
    resp = client.post("/api/v1/recommendations", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_products_count"] == 0
    assert data["recommendations"] == []
    assert data["empty_state_reason"] is not None
    assert "No smartphones found matching" in data["empty_state_reason"]


def test_missing_aspect_evidence_handling(client, recommendation_fixtures):
    """
    Verify that if a phone lacks evidence for a requested aspect (e.g. Display),
    the aspect is marked is_available = False and coverage_ratio is accurately reported.
    """
    req = {
        "min_price": 300.0,
        "max_price": 600.0,
        "priorities": ["Camera", "Display"],
    }
    resp = client.post("/api/v1/recommendations", json=req)
    assert resp.status_code == 200
    data = resp.json()
    top = data["recommendations"][0]
    # Phone A has Camera evidence but NO Display evidence
    assert top["aspect_scores"]["Camera"]["is_available"] is True
    assert top["aspect_scores"]["Display"]["is_available"] is False
    assert top["aspect_scores"]["Display"]["score"] is None
    assert top["coverage_ratio"] == 0.5
    assert any("Display" in lim for lim in top["data_limitations"])


def test_verified_annotation_precedence_and_weighting(client, db_session, recommendation_fixtures):
    """
    Verify that verified human annotations take precedence over model predictions
    and receive higher weighting (1.5x).
    """
    r_a1 = recommendation_fixtures["r_a1"]
    p_a = recommendation_fixtures["p_a"]

    # Add a human verified annotation marking Camera as Negative (e.g. correcting a model prediction)
    anno = ReviewAnnotation(
        review_id=r_a1.id,
        aspect="Camera",
        sentiment="Negative",
        status="VERIFIED",
        annotator_notes="Human expert verified low light artifacting",
    )
    db_session.add(anno)
    db_session.commit()

    # Query aspect scores
    scores_map = recommendation_engine.compute_aspect_scores_for_products(db_session, [p_a.id])
    cam_item = scores_map[p_a.id]["Camera"]
    assert cam_item.is_available is True
    assert cam_item.negative_count == 1
    assert cam_item.positive_count == 0  # Verified annotation overrode the model prediction!
    assert cam_item.score < 50.0  # Dropped below neutral prior


def test_product_comparison_endpoint(client, recommendation_fixtures):
    """Verify side-by-side comparison of 2 or more smartphones."""
    p_a = recommendation_fixtures["p_a"]
    p_b = recommendation_fixtures["p_b"]

    payload = {"product_ids": [p_a.id, p_b.id]}
    resp = client.post("/api/v1/recommendations/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["products"]) == 2
    assert "summary" in data
    assert "aspect_winners" in data
    assert data["aspect_winners"]["Camera"] == p_a.name
    assert data["aspect_winners"]["Battery"] == p_b.name


def test_product_comparison_invalid_requests(client, recommendation_fixtures):
    """Verify validation errors for <2 products in comparison."""
    p_a = recommendation_fixtures["p_a"]
    # Only 1 product ID
    resp = client.post("/api/v1/recommendations/compare", json={"product_ids": [p_a.id]})
    assert resp.status_code == 422

    # Duplicate product ID
    resp_dup = client.post("/api/v1/recommendations/compare", json={"product_ids": [p_a.id, p_a.id]})
    assert resp_dup.status_code == 400


def test_product_score_detail_endpoint(client, recommendation_fixtures):
    """Verify single-device detailed score breakdown."""
    p_a = recommendation_fixtures["p_a"]
    resp = client.get(f"/api/v1/recommendations/products/{p_a.id}/scores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == p_a.id
    assert data["product_name"] == p_a.name
    assert "Camera" in data["aspect_scores"]
    assert "Battery" in data["aspect_scores"]


def test_recommendation_products_summary_endpoint(client, recommendation_fixtures):
    """Verify list of catalog products with prices and evidence counts."""
    resp = client.get("/api/v1/recommendations/products")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    names = [p["product_name"] for p in data]
    assert recommendation_fixtures["p_a"].name in names
