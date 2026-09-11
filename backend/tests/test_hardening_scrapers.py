from backend.app.scrapers.demo_scraper import DemoReviewScraper

def test_scraper_max_reviews_cap():
    scraper = DemoReviewScraper(delay_seconds=0.0)
    # iPhone 15 Pro demo catalog has 7 reviews across 3 pages. Capping at 3.
    batches = list(scraper.scrape("demo://iphone-15-pro", max_pages=3, max_reviews=3))
    total_reviews = sum(len(b["reviews"]) for b in batches if b["success"])
    assert total_reviews == 3

def test_scraper_malformed_html_resilience():
    scraper = DemoReviewScraper(delay_seconds=0.0)
    malformed_html = """
    <div>
      <article class="review-item" data-review-id="bad-01">
        <!-- Missing title and rating -->
        <p class="review-body">Just a body without other fields.</p>
      </article>
      <article class="review-item" data-review-id="bad-02">
        <!-- Empty body must be skipped -->
        <h3 class="review-title">No Body Here</h3>
        <p class="review-body"></p>
      </article>
      <article class="review-item" data-review-id="bad-03">
        <h3 class="review-title">Invalid Rating Format</h3>
        <div class="review-rating" data-score="not-a-number">Five Stars</div>
        <p class="review-body">Text with unparseable rating attribute.</p>
      </article>
    </div>
    """
    reviews = scraper.parse_page(malformed_html, {"product_name": "Test Phone", "brand": "Generic"})
    # bad-01 and bad-03 should be parsed; bad-02 (empty body) should be dropped
    assert len(reviews) == 2
    assert reviews[0].external_review_id == "bad-01"
    assert reviews[0].rating is None
    assert reviews[1].external_review_id == "bad-03"
    assert reviews[1].rating is None

def test_robots_txt_demo_schemes_allowed():
    scraper = DemoReviewScraper(delay_seconds=0.0)
    assert scraper.is_allowed_by_robots("demo://iphone-15-pro") is True
    assert scraper.is_allowed_by_robots("http://mock-review-site.internal/test") is True
