import pytest
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.absa import ReviewAnnotation, ReviewPrediction
from backend.app.services.absa_service import absa_engine, ASPECT_LEXICONS, SEED_BENCHMARK_DATASET


def test_aspect_detection_all_five_aspects():
    """Verify that all five canonical aspects are detected when mentioned."""
    sample = (
        "The battery life lasts all day, and the camera takes crisp photos. "
        "The Snapdragon processor delivers fast gaming performance. "
        "The sleek glass design feels premium, and the OLED display is vibrant and sharp."
    )
    detected = absa_engine.detect_aspects(sample)
    aspect_names = [asp for asp, _ in detected]
    
    assert "Battery" in aspect_names
    assert "Camera" in aspect_names
    assert "Performance" in aspect_names
    assert "Design" in aspect_names
    assert "Display" in aspect_names
    assert len(aspect_names) == 5


def test_aspect_detection_no_aspects():
    """Verify that reviews without smartphone aspects return an empty list."""
    irrelevant = "The package arrived on Tuesday via delivery courier. The box was taped well."
    detected = absa_engine.detect_aspects(irrelevant)
    assert detected == []

    empty_detected = absa_engine.detect_aspects("")
    assert empty_detected == []


def test_multi_aspect_contrastive_sentiment():
    """
    Verify the canonical test case:
    'The camera takes excellent photos, but the battery drains too quickly.'
    Camera -> Positive, Battery -> Negative.
    """
    review_text = "The camera takes excellent photos, but the battery drains too quickly."
    results = absa_engine.predict_text(review_text)

    results_dict = {r.aspect: r for r in results}
    assert "Camera" in results_dict
    assert "Battery" in results_dict

    assert results_dict["Camera"].sentiment == "Positive"
    assert results_dict["Battery"].sentiment == "Negative"
    assert results_dict["Camera"].confidence > 0.5
    assert results_dict["Battery"].confidence > 0.5


def test_neutral_and_negation_sentiment():
    """Verify negation handling and neutral sentiment detection."""
    negated_positive = "The display is not good at all under bright sunlight."
    results = absa_engine.predict_text(negated_positive)
    assert len(results) >= 1
    display_res = next((r for r in results if r.aspect == "Display"), None)
    assert display_res is not None
    assert display_res.sentiment == "Negative"

    neutral_text = "The camera has average 12MP resolution and standard autofocus."
    results_neutral = absa_engine.predict_text(neutral_text)
    cam_res = next((r for r in results_neutral if r.aspect == "Camera"), None)
    assert cam_res is not None
    assert cam_res.sentiment in ["Neutral", "Positive"]


def test_model_training_and_evaluation_metrics():
    """Verify supervised training, train/test splitting, and evaluation metrics generation."""
    train_res = absa_engine.train(db=None, test_size=0.25, random_state=42, include_seed_dataset=True)
    
    assert train_res.status == "success"
    assert train_res.training_samples > 0
    assert train_res.test_samples > 0
    assert 0.0 <= train_res.overall_accuracy <= 1.0
    assert 0.0 <= train_res.overall_macro_f1 <= 1.0
    assert "Positive" in train_res.sentiment_metrics
    assert "Negative" in train_res.sentiment_metrics

    # Test metrics getter
    metrics = absa_engine.get_metrics()
    assert metrics.has_metrics is True
    assert metrics.confusion_matrix is not None
    assert "matrix" in metrics.confusion_matrix
    assert len(metrics.confusion_matrix["matrix"]) == 3  # Positive, Negative, Neutral


def test_api_predict_raw_text(client):
    """Test POST /api/v1/absa/predict endpoint."""
    payload = {
        "text": "The display is gorgeous with 120Hz refresh rate, but performance stutters during heavy gaming."
    }
    response = client.post("/api/v1/absa/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_aspects"] is True
    assert data["aspects_count"] >= 2
    
    aspects = {item["aspect"]: item["sentiment"] for item in data["detected_aspects"]}
    assert "Display" in aspects
    assert "Performance" in aspects
    assert aspects["Display"] == "Positive"
    assert aspects["Performance"] == "Negative"


def test_api_predict_empty_text(client):
    """Test POST /api/v1/absa/predict with empty string returns 400."""
    response = client.post("/api/v1/absa/predict", json={"text": "   "})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_api_predict_no_aspects(client):
    """Test POST /api/v1/absa/predict with text without smartphone aspects."""
    response = client.post("/api/v1/absa/predict", json={"text": "I ordered this last Monday."})
    assert response.status_code == 200
    data = response.json()
    assert data["has_aspects"] is False
    assert data["aspects_count"] == 0
    assert data["detected_aspects"] == []


def test_api_predict_existing_review(client, db_session):
    """Test POST /api/v1/absa/predict/{review_id} with database persistence."""
    prod = Product(name="Galaxy S24", brand="Samsung", canonical_url="https://example.com/s24")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text="Outstanding battery life and great fast charging speed.",
        normalized_review_text="Outstanding battery life and great fast charging speed.",
        rating=5.0,
        source="unit_test",
        content_hash="absa_test_hash_1",
    )
    db_session.add(rev)
    db_session.commit()

    response = client.post(f"/api/v1/absa/predict/{rev.id}?save_prediction=true")
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == rev.id
    assert data["has_aspects"] is True
    assert len(data["detected_aspects"]) >= 1
    assert data["detected_aspects"][0]["aspect"] == "Battery"
    assert data["detected_aspects"][0]["sentiment"] == "Positive"

    # Verify prediction persisted in DB
    preds = db_session.query(ReviewPrediction).filter(ReviewPrediction.review_id == rev.id).all()
    assert len(preds) >= 1
    assert preds[0].aspect == "Battery"
    assert preds[0].sentiment == "Positive"


def test_api_predict_nonexistent_review(client):
    """Test POST /api/v1/absa/predict/{review_id} with invalid id returns 404."""
    response = client.post("/api/v1/absa/predict/999999")
    assert response.status_code == 404


def test_api_model_status_and_metrics(client):
    """Test GET /api/v1/absa/status and GET /api/v1/absa/metrics."""
    status_resp = client.get("/api/v1/absa/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "available_aspects" in status_data
    assert len(status_data["available_aspects"]) == 5
    assert "Battery" in status_data["available_aspects"]

    metrics_resp = client.get("/api/v1/absa/metrics")
    assert metrics_resp.status_code == 200


def test_api_model_train_endpoint(client):
    """Test POST /api/v1/absa/train endpoint."""
    train_payload = {
        "test_size": 0.2,
        "random_state": 42,
        "include_seed_dataset": True,
    }
    response = client.post("/api/v1/absa/train", json=train_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["training_samples"] > 0
    assert data["test_samples"] > 0
    assert "overall_macro_f1" in data


def test_api_human_annotation_workflow(client, db_session):
    """Test creating and listing human ground-truth annotations."""
    prod = Product(name="Pixel 8", brand="Google", canonical_url="https://example.com/pixel8")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text="The camera is fantastic, but the battery drains too quickly.",
        normalized_review_text="The camera is fantastic, but the battery drains too quickly.",
        rating=4.0,
        source="unit_test",
        content_hash="absa_test_hash_2",
    )
    db_session.add(rev)
    db_session.commit()

    # Post annotations
    anno_payload = {
        "annotations": [
            {
                "aspect": "Camera",
                "sentiment": "Positive",
                "status": "VERIFIED",
                "annotator_notes": "Ground truth verified by BCA reviewer",
            },
            {
                "aspect": "Battery",
                "sentiment": "Negative",
                "status": "VERIFIED",
                "annotator_notes": "Explicit negative mention of drain",
            },
        ]
    }
    post_resp = client.post(f"/api/v1/absa/annotate/{rev.id}", json=anno_payload)
    assert post_resp.status_code == 200
    items = post_resp.json()
    assert len(items) == 2

    # Query annotations
    get_resp = client.get(f"/api/v1/absa/annotations?review_id={rev.id}&status=VERIFIED")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["total"] == 2
    assert data["items"][0]["status"] == "VERIFIED"
