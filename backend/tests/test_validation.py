import pytest
from pydantic import ValidationError
from backend.app.schemas.review import RawReviewIn

def test_valid_review_input():
    review = RawReviewIn(
        product_name="Pixel 8 Pro",
        brand="Google",
        raw_review_text="Outstanding display and camera capabilities.",
        rating=4.5
    )
    assert review.product_name == "Pixel 8 Pro"
    assert review.rating == 4.5
    assert review.raw_review_text == "Outstanding display and camera capabilities."

def test_empty_review_text_rejected():
    with pytest.raises(ValidationError):
        RawReviewIn(
            product_name="Pixel 8 Pro",
            raw_review_text="   "
        )

def test_rating_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        RawReviewIn(
            product_name="Pixel 8 Pro",
            raw_review_text="Great battery life",
            rating=5.5
        )

    with pytest.raises(ValidationError):
        RawReviewIn(
            product_name="Pixel 8 Pro",
            raw_review_text="Poor speaker",
            rating=-1.0
        )
