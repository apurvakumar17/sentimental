# SmartReview — Module 1: Smartphone Review Data Collection & Web Scraping System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-38B2AC.svg)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/Tests-45%20Passing-brightgreen.svg)]()

> **SmartReview** is an Aspect-Based Sentiment Analysis and Product Recommendation System for Smartphone Reviews.
> This repository contains the hardened, academically defensible implementation of **Module 1**: "Smartphone Review Data Collection and Web Scraping System".

---

## 1. Scope & Boundaries

### What Module 1 Does
- Collects structured smartphone reviews from permitted demo fixtures and production public review sources (GSM Arena).
- Normalizes text safely (Unicode NFKC, entity unescaping, whitespace collapsing) while strictly preserving casing, punctuation, and all words for future NLP processing.
- Executes a **3-Tier Deduplication Strategy** (External Review ID → Review Permalink URL → Deterministic Content Hash).
- Enforces ethical scraping policies (polite delays with jitter, timeouts, bounded retries with backoff, identifiable `User-Agent`, `robots.txt` awareness, page & review limits, zero anti-bot/CAPTCHA evasion).
- Tracks complete asynchronous job lifecycles (`PENDING -> RUNNING -> COMPLETED / FAILED`).
- Persists data in SQLite with Write-Ahead Logging (`WAL` mode).
- Exposes structured REST APIs via FastAPI and provides an interactive React + Tailwind CSS dashboard.

### What Module 1 Does NOT Do (Strictly Reserved for Future Modules)
- **NO Stopword removal, stemming, or lemmatization** (Reserved for Module 2).
- **NO Tokenization or POS tagging** (Reserved for Module 2).
- **NO Aspect extraction or category tagging** (Reserved for Module 3).
- **NO Sentiment polarity classification** (Reserved for Module 4).
- **NO Model comparison or benchmarking** (Reserved for Module 5).
- **NO Multi-criteria scoring or aggregation** (Reserved for Module 6).
- **NO Product recommendation algorithms** (Reserved for Module 7).

---

## 2. Architecture & Pipeline Roadmap

```
Module 1: Data Collection & Web Scraping (Active)
   │
   ▼  [Contract: review ID, product ID, raw_review_text, normalized_review_text, rating, source]
Module 2: Text Preprocessing Pipeline
   │
   ▼
Module 3: Aspect Extraction (Camera, Battery, Display, Performance)
   │
   ▼
Module 4: Aspect-Level Sentiment Analysis
   │
   ▼
Modules 5–8: Model Evaluation, Multi-Criteria Scoring, & Recommendation Engine
```

### Scraper Class Hierarchy
```
                      +-----------------------------+
                      |      BaseReviewScraper      |
                      |  (Abstract Base Class - ABC)|
                      +-----------------------------+
                                     │
          ┌──────────────────────────┴──────────────────────────┐
          ▼                                                     ▼
+--------------------------+                         +--------------------------+
|    DemoReviewScraper     |                         |  GSMArenaReviewScraper   |
| (Local HTML Fixtures)    |                         | (Public Source Adapter)  |
+--------------------------+                         +--------------------------+
```

---

## 3. Database Entities & Indexing

### Tables
1. **`products`**:
   - `id`: Integer PK
   - `name`: String(255) NOT NULL, INDEX
   - `brand`: String(100) INDEX
   - `canonical_url`: String(500) NULLABLE, UNIQUE
   - `created_at`, `updated_at`: DateTime

2. **`reviews`**:
   - `id`: Integer PK
   - `product_id`: Integer FK, INDEX
   - `scraping_job_id`: Integer FK, INDEX
   - `external_review_id`: String(150), NULLABLE, INDEX
   - `review_title`: String(300), NULLABLE
   - `raw_review_text`: Text NOT NULL (Exact pristine original text)
   - `normalized_review_text`: Text NULLABLE (Unicode NFKC, unescaped HTML, collapsed whitespace)
   - `rating`: Float NULLABLE (0.0 to 5.0)
   - `reviewer_name`: String(150), NULLABLE
   - `review_date_raw`: String(100), NULLABLE
   - `review_date`: Date NULLABLE
   - `source`: String(100) NOT NULL, INDEX
   - `review_url`: String(500) NULLABLE, INDEX
   - `helpful_count`: Integer default 0
   - `content_hash`: String(64) UNIQUE, INDEX
   - `scraped_timestamp`: DateTime NOT NULL
   - **Composite Indexes**:
     - `ix_reviews_prod_ext_id`: `(product_id, source, external_review_id)`
     - `ix_reviews_prod_url`: `(product_id, review_url)`
     - `uq_review_content_hash`: Unique constraint on `content_hash`

3. **`scraping_jobs`**:
   - `id`: Integer PK
   - `job_id`: UUID String(36) UNIQUE, INDEX
   - `target_url`: String(500) NOT NULL
   - `scraper_type`: String(50) NOT NULL
   - `product_id`: Integer FK NULLABLE
   - `status`: String(20) (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`)
   - `max_pages`: Integer default 3
   - `max_reviews`: Integer NULLABLE
   - `pages_attempted`, `successful_pages`, `failed_pages`: Integer counters
   - `reviews_discovered`, `inserted_reviews`, `duplicate_reviews`: Integer counters
   - `error_log`: Text NULLABLE (Sanitized error summary)
   - `started_at`, `finished_at`, `created_at`: DateTime

---

## 4. 3-Tier Deduplication Strategy

To guarantee zero duplicate insertion without relying solely on reviewer names or fragile exact strings:

1. **Tier 1 — Source Review ID**:
   If the source provides a unique review ID (`external_review_id`), verify whether `(product_id, source, external_review_id)` already exists in the current batch or database.
2. **Tier 2 — Review Permalink URL**:
   If the review has a direct permalink (`review_url`), verify whether `(product_id, review_url)` already exists.
3. **Tier 3 — Deterministic Fallback Content Hash**:
   Compute:
   $$\text{SHA256}(\text{product\_id} : \text{source} : \text{safe\_normalize\_text}(\text{raw\_text}).\text{lower}())$$
   Matches identical reviews even when source IDs and URLs are absent.

Both in-flight intra-batch collections and persisted database records are checked.

---

## 5. Safe Data Normalization Strategy

Located in [`backend/app/core/normalization.py`](file:///c:/Users/kumar/Documents/GitHub/sentimental/backend/app/core/normalization.py):
- **Unicode NFKC Normalization**: Converts smart/curly quotes (`“`, `”`, `’`) to standard ASCII equivalents and normalizes non-breaking spaces (`\xa0`).
- **HTML Unescaping & Sanitization**: Decodes entities (`&amp;` -> `&`, `&quot;` -> `"`) and strips residual markup tags (`<br>`, `<p>`).
- **Whitespace Collapsing**: Trims and collapses irregular spaces and newlines into single spaces.
- **Pristine Preservation**: Preserves letter casing, punctuation, grammatical markers, and stopwords so future NLP pipelines in Module 2 have full context.

---

## 6. Scraping Job Lifecycle & Concurrency

Jobs transition through guaranteed states:
```
  [POST /api/v1/jobs/scrape]
              │
              ▼
           PENDING
              │
              ▼  (Worker thread begins)
           RUNNING
              │
      ┌───────┴───────┐
      ▼               ▼
  COMPLETED         FAILED  (Error log sanitized)
```
- Background tasks run with their own dedicated `SessionLocal` database connection.
- A fatal error or unhandled exception is caught and guaranteed to mark the job as `FAILED`, record `finished_at`, and sanitize the `error_log` (removing local filesystem paths).

---

## 7. REST API Endpoints

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System and SQLite connectivity health | 200 |
| `GET` | `/api/v1/products` | List smartphone models with review counts | 200 |
| `GET` | `/api/v1/products/{id}` | Get single product details | 200, 404 |
| `POST` | `/api/v1/products` | Register product manually | 201 |
| `GET` | `/api/v1/reviews` | Paginated reviews (`product_id`, `rating`, `q`) | 200 |
| `GET` | `/api/v1/reviews/{id}` | Get single review item | 200, 404 |
| `POST` | `/api/v1/jobs/scrape` | Dispatch scraping job (`max_pages`, `max_reviews`, `delay`) | 202, 400, 422 |
| `GET` | `/api/v1/jobs` | List historical and active scraping jobs | 200 |
| `GET` | `/api/v1/jobs/{id}` | Real-time status and metrics of a job | 200, 404 |

---

## 8. Supported Scrapers & Adapters

SmartReview provides two production-grade scrapers inheriting from `BaseReviewScraper`:

1. **`demo` (`DemoReviewScraper`)**:
   - Uses local bundled HTML fixtures (`backend/app/scrapers/fixtures/`).
   - Ideal for deterministic offline testing, automated CI, and academic grading without internet connectivity.
   - Scheme: `demo://local-catalog/...`

2. **`gsmarena` (`GSMArenaReviewScraper`)**:
   - Production adapter for permitted public smartphone user reviews and opinions from **GSM Arena**.
   - Supports **ANY** valid GSM Arena smartphone review page (both user opinion threads `*-reviews-*.php` and editorial phone review pages `*-review-*.php` / `reviewcomm-*.php`).
   - Automatically derives `product_name` and `brand` from page metadata (`<h1>` / `<title>`) if not provided upfront by the user.
   - Parses thread containers (`div.user-thread`), extracting external IDs (`uopin` anchors), author names (`li.uname`), dates (`li.upost`), and authentic comment text while cleanly stripping nested quote replies (`span.uinreply`).
   - Handles multi-page opinion and review pagination (`*-reviews-*p{page}.php`, `*-review-*p{page}.php`).
   - Supports local fixture schemes (`gsmarena://sample`, `gsmarena://fixture-a`, `gsmarena://fixture-b`, `gsmarena://malformed`) for fast, offline, and reliable unit tests.

### Scraping Request Example
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/jobs/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php",
    "scraper_type": "gsmarena",
    "product_name": null,
    "brand": null,
    "max_pages": 1,
    "max_reviews": 10,
    "delay_seconds": 2.0
  }'
```

---

## 9. Ethical Web Scraping & Compliance

SmartReview strictly enforces ethical data collection standards:
- **Public & Permitted**: Targets publicly accessible review pages that require zero login or credentials.
- **Robots.txt Adherence**: Automatically checks domain `robots.txt` before fetching web pages.
- **Polite Crawling**: Default 2.0s delay with random jitter (0.5s–1.5s) between pagination requests to prevent server burden.
- **Identifiable User-Agent**: Transmits a transparent User-Agent identifying the research project and contact info: `SmartReview-Bot/1.0 (+https://github.com/apurvakumar17/sentimental; Academic NLP Research Project)`.
- **Zero Anti-Bot / CAPTCHA Evasion**: Contains no proxy rotation, no CAPTCHA solving, and no stealth evasion mechanisms. If an access policy forbids requests, it gracefully terminates with a descriptive error.
- **Deterministic Offline Fixtures**: Bundles full offline HTML fixtures for academic reproducibility and reliable evaluation without live network dependencies.

---

## 10. How Module 2 Will Consume Review Data

Module 2 (Text Preprocessing) will query validated reviews directly via:
```python
# Select reviews ready for NLP preprocessing
reviews = db.query(Review).filter(Review.normalized_review_text.isnot(None)).all()
for r in reviews:
    input_text = r.normalized_review_text
    # Module 2 pipeline: tokenization, lemmatization, stopword removal, pos-tagging...
```

---

## 11. Verification & Test Suite

Run the full automated test suite:
```powershell
.venv\Scripts\python.exe -m pytest backend/tests -v
```
**45 tests passing** covering:
- Database model persistence and constraints
- Schema validation boundary conditions (ratings, URLs, negative limits)
- 3-tier deduplication (external ID, review URL, deterministic content hash)
- Safe text normalization (Unicode NFKC, HTML entities, zero NLP tampering)
- Demo scraper hardening (max reviews limits, malformed HTML resilience, robots.txt)
- GSM Arena production adapter (any review URL validation, review extraction, metadata parsing, quote cleaning, malformed resilience, multi-fixture tests, deduplication)
- Dynamic product auto-derivation and canonical URL association
- Job lifecycle state transitions and error log path sanitization
- API endpoints (upfront scraper validation, 404s, 422s, end-to-end flow)

---

## 12. Running the System

```powershell
# 1. Start Backend API Server
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000

# 2. Start React Dashboard
cd frontend
npm.cmd run dev
```
Open `http://127.0.0.1:5173` in your browser.
Interactive API documentation: `http://127.0.0.1:8000/docs`.
