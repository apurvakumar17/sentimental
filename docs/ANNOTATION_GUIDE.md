# SmartReview: Smartphone Aspect-Based Sentiment Analysis (ABSA) Annotation Guide

This guide establishes the standardized annotation protocol and vocabulary for preparing supervised datasets in **SmartReview: Aspect-Based Sentiment Analysis and Product Recommendation System for Smartphone Reviews Using NLP**.

---

## 1. Objectives & Scaffolding Principles

In Phase 2, dataset records exported from SmartReview include standardized placeholder annotation columns:

| Column Name | Type | Default Value | Purpose |
|---|---|---|---|
| `aspect_labels` | String (JSON array or semicolon-delimited) | `""` | Aspects explicitly or implicitly discussed in the review |
| `sentiment_labels` | String (JSON object or semicolon-delimited) | `""` | Per-aspect sentiment polarity (`positive`, `negative`, `neutral`, `mixed`) |
| `annotation_status` | String | `UNANNOTATED` | State tracking (`UNANNOTATED`, `IN_REVIEW`, `VERIFIED`) |
| `annotator_notes` | String | `""` | Optional rationale, ambiguity notes, or linguistic edge-cases |

> [!IMPORTANT]
> **Zero Label Fabrication Principle**: Never automatically infer ground-truth sentiment labels from star ratings. A 4-star review can express negative sentiment regarding battery life while praising performance. All ground truth must be verified by human annotators adhering to this specification.

---

## 2. Smartphone Aspect Taxonomy

Annotators must classify opinions into the following 10 canonical smartphone aspect categories:

### 1. `Battery`
- **Scope**: Battery capacity (mAh), endurance/screen-on time, standby drain, charging speeds (wired/wireless/reverse), charger compatibility, thermal rise while charging, and battery health degradation.
- *Examples*:
  - *"Battery easily lasts 1.5 days with heavy use."* &rarr; `Battery: positive`
  - *"Drains 20% overnight on standby."* &rarr; `Battery: negative`

### 2. `Camera`
- **Scope**: Primary/wide sensor, ultra-wide, telephoto/periscope zoom lenses, front selfie camera, shutter lag, autofocus, low-light/night photography, HDR tone-mapping, color accuracy, video stabilization (OIS/EIS), 4K/8K recording, portrait edge detection.
- *Examples*:
  - *"The 5x optical zoom captures crisp details."* &rarr; `Camera: positive`
  - *"Front camera over-smoothes skin tones."* &rarr; `Camera: negative`

### 3. `Performance`
- **Scope**: Processor (CPU/GPU/NPU), SoC chipset (Snapdragon, Dimensity, Apple A-series), RAM management, thermal throttling, stuttering, app launch speeds, benchmark scores, multitasking, and sustained high-load gaming (framerate drops).
- *Examples*:
  - *"No lag even when playing Genshin Impact at max settings."* &rarr; `Performance: positive`
  - *"Phone heats up and drops frames after 15 minutes."* &rarr; `Performance: negative`

### 4. `Display`
- **Scope**: Screen resolution, OLED/AMOLED/LTPO technology, refresh rate (60Hz vs 120Hz), touch sampling rate, maximum outdoor brightness (nits), color calibration (DCI-P3, sRGB), HDR10+/Dolby Vision, viewing angles, PWM dimming/flicker.
- *Examples*:
  - *"The 120Hz display is butter smooth and readable in direct sunlight."* &rarr; `Display: positive`
  - *"Noticeable green tint at low brightness."* &rarr; `Display: negative`

### 5. `Design and Build Quality`
- **Scope**: Materials (glass, aluminum, titanium, polycarbonate, vegan leather), weight distribution, ergonomics/in-hand feel, button clickiness, frame rigidity, ingress protection (IP68 water/dust resistance), haptics/vibration motor quality.
- *Examples*:
  - *"Feels premium in the hand with matte glass and aluminum rails."* &rarr; `Design and Build Quality: positive`
  - *"Vibration motor feels hollow and cheap."* &rarr; `Design and Build Quality: negative`

### 6. `Price and Value`
- **Scope**: Retail price, value-for-money ratio, price-to-performance competitiveness against rivals, trade-in deals, perceived overpricing or flagship killer positioning.
- *Examples*:
  - *"Unbeatable value under $400."* &rarr; `Price and Value: positive`
  - *"Way too overpriced for 128GB base storage."* &rarr; `Price and Value: negative`

### 7. `Software and Updates`
- **Scope**: Operating system (Android, iOS), manufacturer skin (One UI, HyperOS, OxygenOS, Pixel UI), bloatware, UI animations, customization, stability/bugs, update policy commitment (e.g. 7 years of OS updates), AI features.
- *Examples*:
  - *"Clean OS without preinstalled junk apps and 5 years guaranteed updates."* &rarr; `Software and Updates: positive`
  - *"Buggy update broke notification banners."* &rarr; `Software and Updates: negative`

### 8. `Audio`
- **Scope**: Stereo speakers, sound loudness, bass response, speaker distortion at high volume, earpiece clarity on phone calls, microphone background noise cancellation, 3.5mm headphone jack presence.
- *Examples*:
  - *"Stereo speakers are loud with deep bass."* &rarr; `Audio: positive`
  - *"Microphone picks up too much wind noise."* &rarr; `Audio: negative`

### 9. `Connectivity`
- **Scope**: Cellular signal reception (5G/4G), Wi-Fi speed and range (Wi-Fi 6E/7), Bluetooth stability, GPS accuracy, NFC for mobile payments, Dual SIM / eSIM support, USB transfer speeds (USB 2.0 vs 3.2).
- *Examples*:
  - *"5G reception is rock solid inside elevators."* &rarr; `Connectivity: positive`
  - *"Bluetooth frequently drops connection to earbuds."* &rarr; `Connectivity: negative`

### 10. `Other`
- **Scope**: Packaging/in-box contents (charger included or omitted), fingerprint scanner speed, Face Unlock reliability, warranty and customer support service.
- *Examples*:
  - *"Ultrasonic fingerprint reader unlocks instantly."* &rarr; `Other: positive`
  - *"Disappointed that no charger is included in the box."* &rarr; `Other: negative`

---

## 3. Sentiment Polarity Definitions

For each identified aspect, assign one of four sentiment polarities:

| Sentiment | Definition | Example |
|---|---|---|
| `positive` | Clear satisfaction, endorsement, or superior performance. | *"Super fast charging."* |
| `negative` | Clear dissatisfaction, defect, frustration, or sub-par performance. | *"Camera takes blurry photos."* |
| `neutral` | Factual or descriptive statement without subjective appraisal. | *"Screen size is 6.7 inches."* |
| `mixed` | Review expresses both positive and negative traits for the *same* aspect. | *"Great zoom in daylight but terrible in low light."* |

---

## 4. Multi-Aspect Reviews & Annotation Formats

A single review frequently contains opinions about multiple aspects:

> **Example Review**:  
> *"The screen is vibrant and battery easily lasts all day, but the phone gets uncomfortably hot during gaming."*

### Standard Annotation Representation

In exported CSV or JSONL files, annotators should format `aspect_labels` and `sentiment_labels` using JSON notation:

#### `aspect_labels`
```json
["Display", "Battery", "Performance"]
```

#### `sentiment_labels`
```json
{
  "Display": "positive",
  "Battery": "positive",
  "Performance": "negative"
}
```

#### `annotation_status`
```text
VERIFIED
```

### Reviews with No Smartphone Aspects
If a review contains only off-topic text (e.g. *"Delivery was fast, Amazon delivery driver was polite"*):
- `aspect_labels`: `[]`
- `sentiment_labels`: `{}`
- `annotation_status`: `IRRELEVANT`
- `annotator_notes`: `"Delivery review, no product aspects mentioned"`

---

## 5. Quality Assurance Checklist for Annotators

1. **Rely on Normalized Review Text**: Use `normalized_review_text` for uniform reading, but refer to `raw_review_text` if context is ambiguous.
2. **Preserve Negations**: Recognize explicit negations (e.g. *"not great"* is `negative`, not `positive`).
3. **Respect Nuance**: Do not label sarcasm as positive (e.g. *"Great, another software update that killed my battery"* &rarr; `Software and Updates: negative`, `Battery: negative`).
4. **Traceability**: Retain `review_id` and `product_id` across external spreadsheet curation so datasets can be joined back to the database.
