# SmartReview — Smartphone Review Data Collection, ABSA & Recommendation System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-38B2AC.svg)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/Tests-113%20Passing-brightgreen.svg)]()

> **SmartReview** is an Aspect-Based Sentiment Analysis and Product Recommendation System for Smartphone Reviews.
> This repository contains Phase 1 (Review Collection & Web Scraping), Phase 2 (Data Quality & Kaggle Ingestion), Phase 3 (Aspect-Based Sentiment Analysis — ABSA), and Phase 4 (Multi-Criteria Product Recommendation & Comparison).

---

## 1. Scope & Boundaries

### What The System Does
- Collects structured smartphone reviews from permitted demo fixtures and production public review sources (GSM Arena).
- Normalizes text safely (Unicode NFKC, entity unescaping, whitespace collapsing) while strictly preserving casing, punctuation, and all words for future NLP processing.
- Executes a **3-Tier Deduplication Strategy** (External Review ID → Review Permalink URL → Deterministic Content Hash).
- Enforces ethical scraping policies (polite delays with jitter, timeouts, bounded retries with backoff, identifiable `User-Agent`, `robots.txt` awareness, page & review limits, zero anti-bot/CAPTCHA evasion).
- Tracks complete asynchronous job lifecycles (`PENDING -> RUNNING -> COMPLETED / FAILED`).
- Persists data in SQLite with Write-Ahead Logging (`WAL` mode).
- Exposes structured REST APIs via FastAPI and provides an interactive React + Tailwind CSS dashboard.

### Scope & Boundaries (Reserved for Future Pipelines)
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
Data Collection & Web Scraping System (Active)
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

---

## 10. Phase 2: Data Quality & NLP-Ready Dataset Preparation Pipeline

Phase 2 builds an end-to-end, reproducible data-quality auditing and dataset packaging pipeline that prepares collected reviews for Aspect-Based Sentiment Analysis (ABSA) while strictly preserving immutable raw review texts.

### 10.1 Key Architecture & Capabilities
1. **Immutable Raw Data Preservation**:
   - `raw_review_text` remains untouched in SQLite storage.
   - Separate `normalized_review_text` stores clean Unicode NFKC text with HTML entity decoding and collapsed spaces.
   - Text stats (`char_count`, `word_count`) computed deterministically.
2. **Multi-Rule Data Quality Assessment**:
   - **Fatal Errors**: Missing review text, normalization-empty text, out-of-bounds ratings (<0.0 or >5.0), missing product relationships.
   - **Review Warnings**: Excessively short (<10 chars), excessively long (>5,000 chars), missing review dates, unrecorded authors.
   - **Duplicate Detection**: Identifies exact hash collisions and potential duplicate records (identical normalized text across same product).
   - **Transparent Quality Score ($0.0 - 100.0$)**:
     $$\text{Quality Score} = \max\left(0, \min\left(100, 100 - \frac{\text{errors} \times 1.0 + \text{warnings} \times 0.15 + \text{exact\_dups} \times 0.25}{\text{total}} \times 100\right)\right)$$
3. **Deterministic Dataset Generation & Export**:
   - Filter by product, rating range, source.
   - Exclude fatal errors and duplicate records from exports *without deleting from SQLite*.
   - Stable deterministic ordering by `review_id ASC`.
   - Export formats: **CSV** (escaped spreadsheet) and **JSONL** (line-delimited JSON).
   - Generates JSON manifests with metadata and cryptographic **SHA-256 fingerprints**.
   - Path-traversal safe downloads restricted to `data/exports/`.
4. **Annotation Scaffolding for ABSA**:
   - Optional unannotated columns: `aspect_labels`, `sentiment_labels`, `annotation_status`, `annotator_notes`.
   - Proposed 10-aspect smartphone taxonomy: *Battery, Camera, Performance, Display, Design and Build Quality, Price and Value, Software and Updates, Audio, Connectivity, Other*.
   - Complete annotation guidelines in [`docs/ANNOTATION_GUIDE.md`](docs/ANNOTATION_GUIDE.md).
5. **Interactive UI Integration**:
   - Dedicated **Dataset & Quality** tab in the React dashboard with real-time health score gauges, error/warning breakdown tiles, preview table, export controls, and manifest archive.

### 10.2 REST API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/datasets/quality` | Evaluates dataset quality across configured rules |
| `POST` | `/api/v1/datasets/preview` | Returns paginated preview of raw vs normalized records |
| `POST` | `/api/v1/datasets/export` | Generates a deterministic CSV or JSONL export with SHA-256 manifest |
| `GET` | `/api/v1/datasets/exports` | Lists all historical export manifests |
| `GET` | `/api/v1/datasets/download/{filename}` | Securely downloads an export file from `data/exports/` |
| `POST` | `/api/v1/system/clear-database` | Permanently deletes all reviews, products, jobs, and metadata |

---

## 11. Verification & Test Suite

Run the full automated test suite:
```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\pytest backend\tests -v
```
**89 tests passing** covering:
- Database model persistence and constraints
- Full database clearing and SQLite autoincrement sequence reset
- Schema validation boundary conditions (ratings, URLs, negative limits)
- 3-tier deduplication (external ID, review URL, deterministic content hash)
- Safe text normalization (Unicode NFKC, HTML entities, zero NLP tampering)
- Demo scraper hardening (max reviews limits, malformed HTML resilience, robots.txt)
- GSM Arena production adapter (URL validation, review extraction, metadata parsing, quote cleaning, malformed resilience, multi-fixture tests, deduplication)
- Dynamic product auto-derivation and canonical URL association
- Job lifecycle state transitions and error log path sanitization
- Safe text preprocessing and sentiment token preservation (emojis, negations, casing)
- Data quality evaluation (clean, error detection, duplicate classification, health score)
- Deterministic dataset preparation and filtering
- CSV and JSONL file export, escaping, and SHA-256 manifest generation
- Directory traversal rejection and export download security
- Reproducible dataset splitting with duplicate cluster grouping
- Dataset API integration (quality assessment, preview, export, download flow)
- **Kaggle 25-column CSV parsing, UTF-8 BOM detection, and row-level validation**
- **Bounded preview without database modification**
- **Batch ingestion of ~50,000 rows with periodic transaction commits (batch size: 500)**
- **Re-import duplicate skipping and idempotency**
- **Product entity reuse across thousands of review rows**
- **Preservation of original source platforms (Amazon, Flipkart) alongside Kaggle provenance**
- **1-to-1 demographic, pricing, and Kaggle aspect/sentiment rating persistence (`ReviewImportMetadata`)**
- **GSM Arena Cloudflare Turnstile challenge detection without stealth evasion**
- **Frontend production build verification (`npm run build`)**

---

## 12. Running the System

```powershell
# 1. Start Backend API Server
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000

# 2. Start React Dashboard
cd frontend
npm run dev
```
Open `http://127.0.0.1:5173` in your browser.
Interactive API documentation: `http://127.0.0.1:8000/docs`.

---

## 13. Phase 2 Extension: Kaggle Dataset Ingestion & Cloudflare Safe Fallback

### 13.1 Kaggle CSV Dataset Overview
To supplement scraped reviews and circumvent third-party anti-bot verification challenges safely, SmartReview includes native support for importing the standard 50,000-row Kaggle Smartphone Review dataset (`Mobile Reviews Sentiment.csv`).

### 13.2 Complete 25-Column Mapping Specification
| # | Kaggle Column | Database Target | Purpose & Handling Policy |
|---|---|---|---|
| 1 | `review_id` | `reviews.external_review_id` | Namespaced with prefix `kaggle_` to prevent collision with scraped IDs |
| 2 | `customer_name` | `reviews.reviewer_name` | Reviewer name; defaults to `Anonymous` if blank |
| 3 | `age` | `review_import_metadata.age` | Integer reviewer demographic age |
| 4 | `brand` | `products.brand` | Smartphone manufacturer name (e.g. Apple, Samsung, OnePlus) |
| 5 | `model` | `products.name` | Smartphone model name; matched case-insensitively to reuse existing `Product` records |
| 6 | `price_usd` | `review_import_metadata.price_usd` | Numeric float price in USD |
| 7 | `price_local` | `review_import_metadata.price_local` | Original raw localized price string (e.g. `₹54,999`) |
| 8 | `currency` | `review_import_metadata.currency` | Currency code or symbol (e.g. `INR`, `₹`, `USD`) |
| 9 | `exchange_rate_to_usd` | `review_import_metadata.exchange_rate_to_usd` | Conversion factor used in dataset |
| 10 | `rating` | `reviews.rating` | Overall rating validated strictly on scale `[0.0, 5.0]` |
| 11 | `review_text` | `reviews.raw_review_text` | Immutable original raw review text (UTF-8, newlines, emojis preserved) |
| 12 | `sentiment` | `review_import_metadata.dataset_sentiment` | Imported sentiment label (`positive`, `negative`, `neutral`) preserved separate from NLP model outputs |
| 13 | `country` | `review_import_metadata.country` | Country origin of review |
| 14 | `language` | `review_import_metadata.language` | Language code / name |
| 15 | `review_date` | `reviews.review_date` & `review_date_raw` | Parsed ISO date if valid; original raw string preserved in `review_date_raw` |
| 16 | `verified_purchase` | `review_import_metadata.verified_purchase` | Boolean flag parsed from `true`/`false`, `1`/`0`, `yes`/`no` |
| 17 | `battery_life_rating` | `review_import_metadata.battery_life_rating` | Imported aspect rating on scale `[1.0, 5.0]` |
| 18 | `camera_rating` | `review_import_metadata.camera_rating` | Imported aspect rating on scale `[1.0, 5.0]` |
| 19 | `performance_rating` | `review_import_metadata.performance_rating` | Imported aspect rating on scale `[1.0, 5.0]` |
| 20 | `design_rating` | `review_import_metadata.design_rating` | Imported aspect rating on scale `[1.0, 5.0]` |
| 21 | `display_rating` | `review_import_metadata.display_rating` | Imported aspect rating on scale `[1.0, 5.0]` |
| 22 | `review_length` | `review_import_metadata.imported_review_length` | Character length provided in dataset |
| 23 | `word_count` | `review_import_metadata.imported_word_count` | Word count provided in dataset |
| 24 | `helpful_votes` | `reviews.helpful_count` | Number of helpful upvotes |
| 25 | `source` | `reviews.source` | Original e-commerce marketplace (e.g. `Amazon`, `Flipkart`, `BestBuy`) |

### 13.3 Architectural Separation & Provenance
- `reviews.ingestion_method`: Explicitly distinguishes `kaggle_import` from `scraper`.
- `reviews.import_job_id`: Foreign key referencing `import_jobs.id`.
- `reviews.source`: Retains the original platform (e.g., `Amazon`, `Flipkart`), avoiding conflation with the import mechanism.
- `ReviewImportMetadata`: 1-to-1 table keeping high-dimensional demographic and aspect metadata without bloating core queries.

### 13.4 Product Reuse & Deduplication
- **Product Reuse**: Brand and model strings are canonicalized (e.g. `Samsung Galaxy S21`). Products are cached in-memory and queried by `(brand, name)`; new `Product` records are created only when a distinct device is encountered.
- **3-Tier Deduplication**:
  1. Namespaced External ID: `kaggle_{row['review_id']}`.
  2. SHA-256 Content Hash: `sha256(f"{product_id}||{clean_text}")`.
- Re-importing the same CSV yields **0 duplicate review insertions** and **0 duplicate product creations**.

### 13.5 GSM Arena Cloudflare Fallback Policy
When public GSM Arena review pages trigger Cloudflare Turnstile human-verification challenges:
1. `GSMArenaReviewScraper` detects challenge HTML signatures (`cf-turnstile`, `cf-chl-`, `<title>Just a moment...`).
2. Crawling immediately halts without retrying.
3. No CAPTCHA-solving, proxy rotation, or stealth bypass is attempted.
4. The scraping job is marked `FAILED` with error code `CLOUDFLARE_CHALLENGE`.
5. The frontend `JobTracker` renders an actionable alert advising the user to switch to the **Dataset Import** tab or use local fixtures (`gsmarena://demo-fixture`).

### 13.6 Ingestion Performance & Scalability
- **Tested on Full Kaggle Dataset**: 50,000 rows, 25 columns, 9.59 MB.
- **Throughput**: ~**6,680 rows/second** in bounded 500-row transactional chunks.
- **Full Ingestion Duration**: **7.48 seconds**.
- **Memory Footprint**: Streaming iterator with fixed-size chunks, maintaining bounded RAM regardless of row count.

---

## 14. Phase 3: Aspect-Based Sentiment Analysis (ABSA)

### 14.1 Objective & Approach
Phase 3 implements an end-to-end, reproducible ABSA engine designed for academic rigor, maintainability, and zero data leakage. Given a review such as:
> *"The camera takes excellent photos, but the battery drains too quickly."*

The model identifies mentioned smartphone aspects and predicts polarities at the clause level:
- **Camera** → **Positive** (Confidence: ~94%, Evidence: *"The camera takes excellent photos"*)
- **Battery** → **Negative** (Confidence: ~94%, Evidence: *"the battery drains too quickly"*)

### 14.2 Five Canonical Smartphone Aspects
1. **Battery**: battery, charging, charge, drain, backup, mAh, endurance, screen-on time.
2. **Camera**: camera, photo, picture, image, video, lens, sensor, zoom, portrait, selfie, night mode.
3. **Performance**: performance, processor, CPU, GPU, speed, snapdragon, bionic, lag, stutter, throttle, gaming.
4. **Design**: design, build, chassis, ergonomics, titanium, aluminum, glass back, lightweight, premium, finish.
5. **Display**: display, screen, OLED, AMOLED, resolution, refresh rate, 120Hz, brightness, viewing angles.

*Multi-Aspect Handling*: If a review contains multiple aspects, each is detected and evaluated independently. If no supported aspects are discussed, the system returns an empty list (`has_aspects=False`) rather than fabricating hallucinated labels.

### 14.3 Model Architecture & Hybrid Pipeline
- **Clause Segmentation**: Regex clause delimiter splitting on sentence boundaries (`.`, `!`, `?`, `;`) and contrastive discourse markers (`but`, `however`, `although`, `while`, `yet`).
- **Aspect Mention Detection**: Domain keyword & n-gram matcher extracting local context evidence windows.
- **Context-Aware Valence & Negation Rule Scorer**: Parses preceding 3-word negation windows (`not`, `never`, `hardly`, `doesn't`, `isn't`) to flip sentiment polarity appropriately.
- **Supervised Classifier**: Multinomial Logistic Regression (`class_weight='balanced'`, `C=2.0`) trained on sublinear TF-IDF features (`ngram_range=(1, 2)`) with hybrid contextual rule priors.
- **Artifact Persistence**: Vectorizer and classifier serialized to `backend/data/models/absa_vectorizer.joblib` and `absa_classifier.joblib`, with evaluation metrics in `absa_metadata.json`.

### 14.4 Ground-Truth Annotations & Separation of Concerns
- **Zero Label Fabrication**: Kaggle imported ratings (`1.0–5.0`) are preserved in `ReviewImportMetadata` and never conflated with verified aspect sentiment ground-truth.
- **ReviewAnnotation**: Dedicated table storing researcher-assigned ground-truth annotations (`VERIFIED`, `IN_REVIEW`, `UNANNOTATED`).
- **ReviewPrediction**: Stores model inference outputs with model version (`absa-hybrid-v1.0`), confidence, and evidence clauses without mutating immutable review text.

### 14.5 ABSA Endpoints
- `POST /api/v1/absa/predict` — Analyze raw review text in real-time.
- `POST /api/v1/absa/predict/{review_id}` — Run ABSA on database review and optionally persist predictions.
- `GET /api/v1/absa/status` — Model deployment readiness, annotation statistics, and artifact status.
- `POST /api/v1/absa/train` — Reproducible training pipeline with configurable test split and seed benchmark.
- `GET /api/v1/absa/metrics` — Held-out evaluation report, macro metrics, and confusion matrix.
- `POST /api/v1/absa/annotate/{review_id}` — Record verified human ground-truth labels.
- `GET /api/v1/absa/annotations` — Paginated list of human annotations.
- `GET /api/v1/absa/predictions/{review_id}` — Retrieve historical model predictions for a review.

---

## 15. Phase 4: Smartphone Product Recommendation System

### 15.1 Objective & Architecture
Phase 4 builds a modular, explainable multi-criteria smartphone recommendation engine that ranks catalog devices based on:
1. **Budget Constraints**: Minimum and maximum price boundaries in USD (derived from reliable Kaggle import metadata and catalog price attributes).
2. **Brand Preferences**: Filtering to desired manufacturers (e.g., Apple, Samsung, Google, Xiaomi, Motorola, Realme) or evaluating all brands.
3. **Aspect Priority Ordering & Custom Weighting**: Explicit ranking of the 5 canonical aspects (Battery, Camera, Performance, Design, Display).
4. **Bayesian Aspect-Level Evidence**: Empirical Bayes credibility smoothing derived from stored ABSA predictions and human annotations.
5. **Zero Hallucination Policy**: If reliable ABSA evidence is absent for an aspect, it is explicitly flagged as `is_available: false` and `score: null`—never fabricated or treated as neutral.

```
┌────────────────────────────────────────────────────────┐
│                   User Request Filters                 │
│  • Budget ($300 – $600)   • Brands (e.g., All / Moto) │
│  • Priorities: 1. Camera, 2. Battery, 3. Performance   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              Recommendation Service (Engine)           │
│  1. Filter eligible products (Budget & Brand matching) │
│  2. Load stored ABSA predictions & human annotations   │
│  3. Deduplicate evidence per (review_id, aspect)       │
│  4. Compute Bayesian credibility score per aspect      │
│  5. Calculate multi-criteria weighted recommendation   │
│  6. Generate explainable strengths, weaknesses & notes │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            FastAPI Endpoints & React Dashboard         │
│  • Ranked Recommendation Cards with aspect gauges      │
│  • Dynamic Side-by-Side Comparison Matrix (2–4 phones) │
│  • Bayesian Credibility Inspector Modal                │
└────────────────────────────────────────────────────────┘
```

---

### 15.2 Aspect-Level Scoring Formula (Empirical Bayes)
To prevent a smartphone with a single 5-star review from outranking a device with hundreds of reviews, aspect scores are calculated using **Bayesian credibility shrinkage** towards an uninformative prior mean ($\mu_0 = 50.0$) with damping parameter $m = 3.0$ effective reviews:

$$\text{Aspect Score} = \frac{(W_{\text{pos}} + 0.5 \cdot W_{\text{neu}}) \cdot 100 + m \cdot \mu_0}{N_{\text{eff}} + m}$$

Where:
- $W_{\text{pos}} = \sum_{\text{Positive}} w_i$
- $W_{\text{neu}} = \sum_{\text{Neutral}} w_i$
- $W_{\text{neg}} = \sum_{\text{Negative}} w_i$
- $N_{\text{eff}} = W_{\text{pos}} + W_{\text{neu}} + W_{\text{neg}}$
- Prior parameters: $m = 3.0$ effective reviews, $\mu_0 = 50.0$ neutral prior.

**Evidence Weighting ($w_i$):**
- **Verified Human Annotation**: $w_i = 1.50$ (ground-truth precedence).
- **Automated ABSA Model Prediction**: $w_i = 1.00 \times \text{confidence}$ (confidence-discounted).
- **Deduplication**: If a review contains both a verified annotation and a model prediction for the same aspect, the human annotation takes absolute precedence.

---

### 15.3 Multi-Criteria Weighted Ranking Formula
When a user specifies an ordered list of priorities $[A_1, A_2, \dots, A_k]$, default rank-decay multipliers are assigned:
- Priority 1: Multiplier = $5.0\times$
- Priority 2: Multiplier = $2.5\times$
- Priority 3: Multiplier = $1.5\times$
- Priority 4: Multiplier = $1.0\times$
- Priority 5: Multiplier = $0.5\times$

*(Users can also provide custom continuous weights through `priority_weights` in the API request).*

The overall composite score is calculated as:
$$\text{Overall Score} = \frac{\sum_{i=1}^k S(A_i) \cdot W(A_i)}{\sum_{i=1}^k W(A_i)}$$

Where $S(A_i)$ is the Bayesian aspect score (0–100) for aspect $A_i$. If an aspect is unavailable, it is excluded from the denominator to avoid penalizing phones for missing reviews, while generating an explicit data limitation note.

---

### 15.4 Product Comparison Engine
The recommendation engine provides a multi-product side-by-side comparison endpoint (`POST /api/v1/recommendations/compare`):
- Accepts 2 to 5 product IDs.
- Calculates aspect winners dynamically based on Bayesian aspect scores.
- Contrasts evidence volume ($n$ reviews, positive %, neutral %, negative %).
- Highlights distinct standout strengths ($\ge 68/100$) and weaknesses ($\le 45/100$).
- Enforces strict currency fidelity (compares clean USD figures without guessing unverified FX rates).

---

### 15.5 Recommendation Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/recommendations` | `POST` | Generates ranked smartphone recommendations for user budget, brands, and aspect priorities. |
| `/api/v1/recommendations/aspects` | `GET` | Returns the 5 supported smartphone aspects and their keywords. |
| `/api/v1/recommendations/products` | `GET` | Returns catalog smartphone summary with USD prices and review counts. |
| `/api/v1/recommendations/compare` | `POST` | Generates side-by-side comparison for 2–5 smartphones with aspect winners. |
| `/api/v1/recommendations/products/{id}/scores` | `GET` | Retrieves full Bayesian credibility breakdown, weights, and evidence counts for a specific smartphone. |
| `/api/v1/recommendations/sync-predictions` | `POST` | Precomputes and syncs ABSA review predictions across warehouse products. |

#### Example Request: Ranked Recommendations
```json
POST /api/v1/recommendations
{
  "min_price": 300.0,
  "max_price": 600.0,
  "brands": ["Realme", "Motorola", "Xiaomi"],
  "priorities": ["Camera", "Battery", "Performance"],
  "min_evidence_count": 2,
  "limit": 5
}
```

#### Example Response:
```json
{
  "total_eligible_products": 5,
  "matched_products_count": 5,
  "applied_budget_filter": "$300.0 – $600.0",
  "applied_brand_filter": ["Realme", "Motorola", "Xiaomi"],
  "priorities_evaluated": ["Camera", "Battery", "Performance"],
  "recommendations": [
    {
      "rank": 1,
      "product_id": 8,
      "product_name": "Realme 12 Pro",
      "brand": "Realme",
      "price_usd": 393.08,
      "overall_score": 61.7,
      "aspect_scores": {
        "Battery": { "score": 55.0, "is_available": true, "evidence_count": 5 },
        "Camera": { "score": 63.6, "is_available": true, "evidence_count": 3 },
        "Performance": { "score": 66.6, "is_available": true, "evidence_count": 12 },
        "Design": { "score": 55.5, "is_available": true, "evidence_count": 6 },
        "Display": { "score": 61.3, "is_available": true, "evidence_count": 3 }
      },
      "explanation": "Performs strongly in your #1 priority Camera with an aspect score of 63.6/100 based on 3 reviews.",
      "strengths": [],
      "weaknesses": [],
      "data_limitations": []
    }
  ]
}
```

---

### 15.6 Academic Disclaimer & Limitations
1. **Sample Bias**: Recommendations are computed strictly from available crawled and imported reviews in the local SQLite database. They do not constitute an objective engineering benchmark.
2. **Pricing Availability**: Price fields reflect representative import metadata (`price_usd`). Where prices are missing, the UI clearly labels them as `Price Unavailable` rather than guessing arbitrary amounts.
3. **No Hallucination**: An aspect without review evidence is marked `Unavailable`, not assigned a default neutral score of 50.

