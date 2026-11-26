import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_recall_fscore_support,
    accuracy_score,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.normalization import safe_normalize_text
from backend.app.models.absa import ReviewAnnotation, ReviewPrediction
from backend.app.models.review import Review
from backend.app.schemas.absa import (
    ASPECTS_LIST,
    SENTIMENTS_LIST,
    AspectSentimentResult,
    ABSAPredictResponse,
    ABSAModelStatus,
    ABSATrainResponse,
    ABSAMetricsResponse,
)

logger = logging.getLogger("smartreview.absa")

# Model paths
MODELS_DIR = settings.MODELS_DIR
VECTORIZER_PATH = MODELS_DIR / "absa_vectorizer.joblib"
CLASSIFIER_PATH = MODELS_DIR / "absa_classifier.joblib"
METRICS_PATH = MODELS_DIR / "absa_metadata.json"

MODEL_VERSION = "absa-hybrid-v1.0"

# Aspect Keywords & Patterns
ASPECT_LEXICONS: Dict[str, Set[str]] = {
    "Battery": {
        "battery", "batteries", "backup", "endurance", "mah", "sot",
        "screen-on", "standby", "battery life", "battery-life",
    },
    "Charging": {
        "charge", "charging", "charger", "chargers", "fast charging", "fast charge",
        "slow charging", "wireless charging", "reverse charging", "recharge",
        "watt", "watts", "warp charge", "supervooc", "hypercharge", "pd charging",
        "adapter", "adaptor", "power brick",
    },
    "Camera": {
        "camera", "cameras", "photo", "photos", "picture", "pictures", "pic",
        "pics", "image", "images", "video", "videos", "lens", "lenses",
        "sensor", "sensors", "zoom", "optical zoom", "telephoto", "macro",
        "wide", "ultrawide", "ultra-wide", "selfie", "selfies", "portrait",
        "portraits", "night mode", "low light", "low-light", "shutter",
        "megapixel", "mp", "4k", "8k", "hdr", "exposure", "focus", "autofocus",
        "front camera", "rear camera", "stabilization", "ois",
    },
    "Performance": {
        "performance", "processor", "processors", "cpu", "gpu", "chip", "chips",
        "chipset", "chipsets", "soc", "snapdragon", "bionic", "dimensity",
        "exynos", "tensor", "ram", "memory", "speed", "fast", "snappy",
        "smooth", "smoothness", "lag", "lags", "laggy", "lagging", "stutter",
        "stutters", "stuttering", "slow", "sluggish", "fps", "frame rate",
        "framerate", "gaming", "game", "games", "multitasking", "benchmark",
    },
    "Design": {
        "design", "looks", "look", "aesthetic", "aesthetics", "build",
        "build quality", "body", "frame", "chassis", "finish", "materials",
        "metal", "aluminum", "aluminium", "glass", "plastic", "polycarbonate",
        "titanium", "in-hand", "in hand", "hand feel", "ergonomics", "grip",
        "weight", "heavy", "lightweight", "light", "bulky", "slim", "sleek",
        "premium", "color", "colors", "buttons", "durable", "durability",
    },
    "Display": {
        "display", "screen", "panel", "panels", "amoled", "oled", "lcd",
        "ips", "refresh rate", "120hz", "90hz", "60hz", "144hz", "hz",
        "hertz", "brightness", "bright", "nits", "resolution", "1080p", "1440p",
        "hdr", "hdr10", "dolby vision", "viewing angles", "viewing angle",
        "colors", "vibrant", "sharp", "sharpness", "crisp", "touch sampling",
        "bezels", "bezel", "punch hole", "notch", "outdoor visibility",
    },
    "Audio & Sound": {
        "speaker", "speakers", "sound", "audio", "volume", "loud", "loudness",
        "bass", "treble", "stereo", "dual speakers", "stereo speakers",
        "headphone", "headphone jack", "3.5mm", "earpiece", "microphone",
        "mic", "dolby atmos", "sound quality", "audio quality", "music",
        "ringtone", "speakerphone", "clarity",
    },
    "Software & OS": {
        "software", "os", "operating system", "ui", "user interface", "android",
        "ios", "hyperos", "miui", "oneui", "one ui", "oxygenos", "coloros",
        "realmeui", "funtouch", "stock android", "bloatware", "adware",
        "update", "updates", "patch", "security patch", "customization",
        "bugs", "buggy", "glitches", "smooth os",
    },
    "Value for Money": {
        "price", "pricing", "value", "worth", "money", "cost", "costly",
        "expensive", "budget", "affordable", "cheap", "overpriced",
        "value for money", "vfm", "pocket friendly", "bang for buck",
        "deal", "worth the money", "worth it", "waste of money",
    },
    "Connectivity": {
        "connectivity", "5g", "4g", "lte", "network", "reception", "signal",
        "wifi", "wi-fi", "bluetooth", "cellular", "sim", "dual sim",
        "esim", "e-sim", "hotspot", "gps", "nfc", "call quality", "calls",
    },
    "Biometrics": {
        "fingerprint", "finger print", "face unlock", "facial recognition",
        "biometrics", "in-display fingerprint", "scanner", "optical sensor",
    },
    "Thermal & Cooling": {
        "heat", "heats", "heating", "warm", "hot", "overheating", "overheat",
        "thermal", "thermals", "cooling", "vapor chamber", "throttling",
        "throttle", "temperature",
    },
    "Storage": {
        "storage", "internal storage", "rom", "128gb", "256gb", "512gb",
        "1tb", "microsd", "sd card", "memory card", "expandable", "capacity",
    },
    "Haptics": {
        "haptic", "haptics", "haptic feedback", "vibration", "vibration motor",
        "tactile", "tactile feedback",
    },
    "Water Resistance": {
        "water resistance", "waterproof", "water proof", "water resistant",
        "ip68", "ip67", "splash proof", "splash resistant",
    },
    "Accessories": {
        "accessories", "accessory", "back cover", "free case", "case in box",
        "earphones", "earbuds", "stylus", "s-pen", "s pen",
    },
}

# Open dynamic aspect patterns for words not in the predefined lexicon
OPEN_ASPECT_DIRECT_PATTERNS: Dict[str, str] = {
    "Flashlight": r"\b(flashlight|torch light|torch)\b",
    "Customer Service": r"\b(customer service|customer support|warranty support|after sales service)\b",
    "SIM & Storage Tray": r"\b(sim tray|dual sim tray|sim slot|micro sd slot)\b",
}

# Non-aspect stopwords to prevent false aspect extractions
NON_ASPECT_WORDS: Set[str] = {
    "phone", "phones", "device", "devices", "mobile", "mobiles", "product", "products",
    "item", "items", "unit", "units", "one", "thing", "things", "lot", "way", "delivery",
    "courier", "package", "packaging", "box", "taped", "seller", "amazon", "flipkart",
    "time", "times", "day", "days", "week", "weeks", "month", "months", "year", "years",
    "purchase", "buy", "order", "ordered", "today", "yesterday", "tomorrow", "use",
    "user", "review", "opinion", "money", "person", "people", "brand", "model",
}

# Sentiment Lexicon & Valences
POSITIVE_TERMS: Set[str] = {
    "good", "great", "excellent", "amazing", "awesome", "fantastic", "superb",
    "stellar", "top-notch", "love", "loved", "loving", "best", "perfect",
    "impressive", "smooth", "snappy", "fast", "crisp", "sharp", "gorgeous",
    "beautiful", "premium", "durable", "solid", "reliable", "decent", "fine",
    "exceptional", "flawless", "satisfying", "pleasant", "long-lasting", "lasts",
    "worth", "incredible", "outstanding", "brilliant", "delight", "pleased",
    "pleasure", "breathtaking", "vivid", "punchy",
}

NEGATIVE_TERMS: Set[str] = {
    "bad", "terrible", "horrible", "awful", "poor", "worse", "worst", "lag",
    "lags", "laggy", "slow", "sluggish", "stutter", "stutters", "drain", "drains",
    "draining", "drained", "heat", "heats", "heating", "hot", "warm", "overheating",
    "blur", "blurry", "dim", "washed", "fuzzy", "cheap", "fragile",
    "scratches", "buggy", "defective", "disappointing", "disappointed", "hate",
    "hated", "useless", "garbage", "trash", "annoying", "fails", "failed",
    "drops", "dropping", "mediocre", "subpar", "abysmal", "unacceptable",
}

NEGATION_TERMS: Set[str] = {
    "not", "no", "never", "hardly", "barely", "scarcely", "doesn't", "dont",
    "don't", "doesnt", "didnt", "didn't", "isnt", "isn't", "arent", "aren't",
    "wont", "won't", "cant", "can't", "cannot", "neither", "nor", "without",
}

# Standard seed dataset for reproducible academic training and benchmarking
SEED_BENCHMARK_DATA: List[Dict[str, Any]] = [
    # Battery examples
    {"text": "The battery life is phenomenal, easily lasts two days on a charge.", "aspect": "Battery", "sentiment": "Positive"},
    {"text": "Super fast charging fills the battery in under 30 minutes.", "aspect": "Battery", "sentiment": "Positive"},
    {"text": "Battery backup is solid and reliable for all-day usage.", "aspect": "Battery", "sentiment": "Positive"},
    {"text": "Battery drains too quickly even on basic standby.", "aspect": "Battery", "sentiment": "Negative"},
    {"text": "Disappointed with battery life, requires charging twice a day.", "aspect": "Battery", "sentiment": "Negative"},
    {"text": "Severe battery drain after the latest software update.", "aspect": "Battery", "sentiment": "Negative"},
    {"text": "The phone comes with a 5000mAh battery pack.", "aspect": "Battery", "sentiment": "Neutral"},
    {"text": "Battery performance is standard and as expected for this size.", "aspect": "Battery", "sentiment": "Neutral"},

    # Camera examples
    {"text": "The camera captures breathtaking portraits with vivid colors.", "aspect": "Camera", "sentiment": "Positive"},
    {"text": "Low light photos are surprisingly sharp and detailed.", "aspect": "Camera", "sentiment": "Positive"},
    {"text": "Video stabilization and zoom lens are outstanding.", "aspect": "Camera", "sentiment": "Positive"},
    {"text": "The front selfie camera takes blurry and washed out photos.", "aspect": "Camera", "sentiment": "Negative"},
    {"text": "Camera autofocus is terribly slow and loses subject constantly.", "aspect": "Camera", "sentiment": "Negative"},
    {"text": "Shutter lag ruins fast action shots on this camera.", "aspect": "Camera", "sentiment": "Negative"},
    {"text": "It features a 50 megapixel main sensor and wide angle lens.", "aspect": "Camera", "sentiment": "Neutral"},
    {"text": "The camera app includes standard pro and panorama modes.", "aspect": "Camera", "sentiment": "Neutral"},

    # Performance examples
    {"text": "Lightning fast performance with butter smooth multitasking.", "aspect": "Performance", "sentiment": "Positive"},
    {"text": "The Snapdragon processor runs high end games without dropping frames.", "aspect": "Performance", "sentiment": "Positive"},
    {"text": "Everything opens instantly and animations never lag.", "aspect": "Performance", "sentiment": "Positive"},
    {"text": "Noticeable lag and stuttering while switching between apps.", "aspect": "Performance", "sentiment": "Negative"},
    {"text": "The phone overheats and thermal throttles after ten minutes of gaming.", "aspect": "Performance", "sentiment": "Negative"},
    {"text": "Extremely slow performance with frequent freezes and crashes.", "aspect": "Performance", "sentiment": "Negative"},
    {"text": "Equipped with 8GB RAM and an octa core processor.", "aspect": "Performance", "sentiment": "Neutral"},
    {"text": "Benchmark scores align with other mid-range chipsets.", "aspect": "Performance", "sentiment": "Neutral"},

    # Design examples
    {"text": "Gorgeous premium design with sleek titanium rails and frosted glass.", "aspect": "Design", "sentiment": "Positive"},
    {"text": "Feels very solid, balanced, and ergonomic in hand.", "aspect": "Design", "sentiment": "Positive"},
    {"text": "Minimalist aesthetics and lightweight build make it a pleasure to hold.", "aspect": "Design", "sentiment": "Positive"},
    {"text": "Cheap plastic frame feels flimsy and scratches easily.", "aspect": "Design", "sentiment": "Negative"},
    {"text": "The phone is overly heavy, bulky, and difficult to grip.", "aspect": "Design", "sentiment": "Negative"},
    {"text": "Sharp edges make the phone uncomfortable to hold without a case.", "aspect": "Design", "sentiment": "Negative"},
    {"text": "The device weighs approximately 190 grams and has a glass back.", "aspect": "Design", "sentiment": "Neutral"},
    {"text": "Available in black, silver, and dark blue color options.", "aspect": "Design", "sentiment": "Neutral"},

    # Display examples
    {"text": "The 120Hz AMOLED display is gorgeous, punchy, and ultra bright.", "aspect": "Display", "sentiment": "Positive"},
    {"text": "Screen outdoor visibility is spectacular under direct sunlight.", "aspect": "Display", "sentiment": "Positive"},
    {"text": "Vibrant colors and razor sharp resolution make watching videos a joy.", "aspect": "Display", "sentiment": "Positive"},
    {"text": "Dull screen with terrible viewing angles and noticeable flickering.", "aspect": "Display", "sentiment": "Negative"},
    {"text": "Display brightness is too low to read outdoors in daylight.", "aspect": "Display", "sentiment": "Negative"},
    {"text": "Annoying green tint on the screen at low brightness levels.", "aspect": "Display", "sentiment": "Negative"},
    {"text": "Features a 6.7 inch OLED screen with 1080p resolution.", "aspect": "Display", "sentiment": "Neutral"},
    {"text": "The display has a center hole punch cutout for the front camera.", "aspect": "Display", "sentiment": "Neutral"},

    # Audio & Sound examples
    {"text": "The stereo speakers are remarkably loud, clear, and deliver rich bass.", "aspect": "Audio & Sound", "sentiment": "Positive"},
    {"text": "Crystal clear call quality and excellent microphone noise cancellation.", "aspect": "Audio & Sound", "sentiment": "Positive"},
    {"text": "Audio from the speaker sounds tinny, muffled, and distorts at high volume.", "aspect": "Audio & Sound", "sentiment": "Negative"},
    {"text": "Disappointed that there is no 3.5mm headphone jack on this model.", "aspect": "Audio & Sound", "sentiment": "Negative"},
    {"text": "It includes dual bottom-firing speakers and standard Bluetooth 5.3 audio.", "aspect": "Audio & Sound", "sentiment": "Neutral"},

    # Software & OS examples
    {"text": "Clean bloatware-free software with intuitive gestures and smooth animations.", "aspect": "Software & OS", "sentiment": "Positive"},
    {"text": "Timely software updates and a lightweight user interface.", "aspect": "Software & OS", "sentiment": "Positive"},
    {"text": "Buggy UI packed with annoying adware and unwanted pre-installed apps.", "aspect": "Software & OS", "sentiment": "Negative"},
    {"text": "The latest OS update introduced frequent app crashes and interface freezes.", "aspect": "Software & OS", "sentiment": "Negative"},
    {"text": "Ships with Android 14 out of the box with guaranteed two years of OS updates.", "aspect": "Software & OS", "sentiment": "Neutral"},

    # Value for Money examples
    {"text": "Incredible value for money, offers flagship tier specs at a mid-range price.", "aspect": "Value for Money", "sentiment": "Positive"},
    {"text": "Unbeatable pricing for the hardware offered, absolute bang for buck.", "aspect": "Value for Money", "sentiment": "Positive"},
    {"text": "Way overpriced for what it provides, terrible value compared to competitors.", "aspect": "Value for Money", "sentiment": "Negative"},
    {"text": "Waste of hard earned money, definitely not worth the premium retail price.", "aspect": "Value for Money", "sentiment": "Negative"},
    {"text": "Priced competitively within the sub-$400 budget smartphone bracket.", "aspect": "Value for Money", "sentiment": "Neutral"},

    # Connectivity examples
    {"text": "Blazing fast 5G speeds with excellent cellular reception and rock-solid WiFi.", "aspect": "Connectivity", "sentiment": "Positive"},
    {"text": "Frequent call drops and very weak mobile network signal in indoor areas.", "aspect": "Connectivity", "sentiment": "Negative"},
    {"text": "Supports dual SIM 5G standby, WiFi 6, and NFC for contactless payments.", "aspect": "Connectivity", "sentiment": "Neutral"},

    # Charging examples
    {"text": "Super fast 80W charging fills the battery from empty to 100% in 25 minutes.", "aspect": "Charging", "sentiment": "Positive"},
    {"text": "Frustratingly slow charging speed, takes over two hours to reach full capacity.", "aspect": "Charging", "sentiment": "Negative"},
    {"text": "Supports 33W wired charging and does not include wireless charging.", "aspect": "Charging", "sentiment": "Neutral"},
]

SEED_BENCHMARK_DATASET = SEED_BENCHMARK_DATA


class ABSAEngine:
    """
    Modular Aspect-Based Sentiment Analysis Engine.
    Handles:
      1. Aspect Category Detection via domain vocabulary and clause segmentation.
      2. Aspect-level context window and evidence extraction.
      3. Hybrid Sentiment Polarity Classification (TF-IDF Classifier + Valence Rules).
      4. Artifact persistence and model evaluation metrics calculation.
    """

    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.classifier: Optional[LogisticRegression] = None
        self.metadata: Optional[Dict[str, Any]] = None
        self.is_trained: bool = False
        self.load_model()

    def load_model(self) -> bool:
        """Loads serialized model artifacts if available on disk."""
        if VECTORIZER_PATH.exists() and CLASSIFIER_PATH.exists():
            try:
                self.vectorizer = joblib.load(VECTORIZER_PATH)
                self.classifier = joblib.load(CLASSIFIER_PATH)
                if METRICS_PATH.exists():
                    with open(METRICS_PATH, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                self.is_trained = True
                logger.info(f"ABSA model loaded successfully from {MODELS_DIR}")
                return True
            except Exception as exc:
                logger.warning(f"Failed to load ABSA artifacts: {exc}")
                self.is_trained = False
                return False
        self.is_trained = False
        return False

    def save_model(self, metrics: Dict[str, Any]) -> None:
        """Serializes trained vectorizer, classifier, and metadata to disk."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        if self.vectorizer and self.classifier:
            joblib.dump(self.vectorizer, VECTORIZER_PATH)
            joblib.dump(self.classifier, CLASSIFIER_PATH)
            with open(METRICS_PATH, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
            self.metadata = metrics
            self.is_trained = True
            logger.info("ABSA model artifacts saved to disk.")

    def detect_aspects(self, text: str) -> List[Tuple[str, str]]:
        """
        Detects all discussed smartphone aspects and hardware/software features in text.
        Supports full open/dynamic aspect extraction beyond fixed categories.
        Returns a list of (aspect_name, evidence_clause) tuples.
        """
        if not text or not text.strip():
            return []

        norm_text = safe_normalize_text(text)
        
        # Split text into sentence/clause segments
        clause_delimiters = r"[.!?;:]|\b(?:but|however|although|though|whereas|yet|while|and)\b"
        raw_clauses = re.split(clause_delimiters, norm_text, flags=re.IGNORECASE)
        clauses = [c.strip() for c in raw_clauses if len(c.strip()) > 3]
        if not clauses:
            clauses = [norm_text]

        detected_aspects_map: Dict[str, List[str]] = {}

        # 1. Match against domain taxonomy lexicons
        for aspect_name, keywords in ASPECT_LEXICONS.items():
            matching_clauses: List[str] = []
            for clause in clauses:
                tokens = set(re.findall(r"\b[a-z0-9\-]+\b", clause.lower()))
                for kw in keywords:
                    if " " in kw:
                        if kw in clause.lower():
                            matching_clauses.append(clause)
                            break
                    else:
                        if kw in tokens:
                            matching_clauses.append(clause)
                            break

            if matching_clauses:
                combined_evidence = " ... ".join(matching_clauses[:2])
                detected_aspects_map[aspect_name] = combined_evidence

        # 2. Match direct open aspect patterns (e.g. Flashlight, Customer Service)
        for aspect_name, pattern in OPEN_ASPECT_DIRECT_PATTERNS.items():
            if aspect_name not in detected_aspects_map:
                for clause in clauses:
                    if re.search(pattern, clause, flags=re.IGNORECASE):
                        detected_aspects_map[aspect_name] = clause
                        break

        # 3. Dynamic candidate noun extraction for novel aspects
        # Look for opinion-target pairs like "the <noun> is <adj>" or "<adj> <noun>"
        # Only when no other aspect was already extracted from that clause
        for clause in clauses:
            clause_lower = clause.lower()
            # Pattern: <noun> (is|was|feels|seems) (very|quite|really)? <sentiment_adj>
            adj_tokens = r"(?:good|great|excellent|amazing|awesome|superb|impressive|decent|bad|terrible|horrible|awful|poor|slow|fast|loud|quiet|sharp|blurry|sturdy|fragile|durable)"
            target_matches = re.findall(
                rf"\b([a-z]{{3,15}})\s+(?:is|was|are|were|feels|seems|looks)\s+(?:very\s+|quite\s+|super\s+)?{adj_tokens}\b",
                clause_lower
            )
            # Pattern: <sentiment_adj> <noun>
            attrib_matches = re.findall(
                rf"\b{adj_tokens}\s+([a-z]{{3,15}})\b",
                clause_lower
            )
            candidates = set(target_matches + attrib_matches)
            for cand in candidates:
                if cand not in NON_ASPECT_WORDS and len(cand) >= 4:
                    # Title-case candidate
                    cand_aspect = cand.capitalize()
                    # Check if already covered by an existing aspect
                    already_covered = any(
                        cand in [kw.lower() for kw in kws]
                        for kws in ASPECT_LEXICONS.values()
                    )
                    if not already_covered and cand_aspect not in detected_aspects_map:
                        detected_aspects_map[cand_aspect] = clause

        # Return list of detected aspects: canonical aspects first, then any open dynamic aspects
        results: List[Tuple[str, str]] = []
        seen: Set[str] = set()

        # Preferred ordering for standard aspects
        for aspect in ASPECTS_LIST:
            if aspect in detected_aspects_map and aspect not in seen:
                results.append((aspect, detected_aspects_map[aspect]))
                seen.add(aspect)

        # Add any dynamically discovered open aspects
        for aspect, evidence in detected_aspects_map.items():
            if aspect not in seen:
                results.append((aspect, evidence))
                seen.add(aspect)

        return results

    def _lexical_sentiment_score(self, evidence_text: str) -> Tuple[str, float]:
        """
        Calculates sentiment polarity using context-aware lexical valence and negation parsing.
        Returns (Sentiment: 'Positive'|'Negative'|'Neutral', Confidence: float).
        """
        words = re.findall(r"\b[a-z0-9']+\b", evidence_text.lower())
        if not words:
            return "Neutral", 0.50

        pos_score = 0.0
        neg_score = 0.0

        for i, word in enumerate(words):
            # Inspect preceding 3 words for negation
            window_start = max(0, i - 3)
            preceding = words[window_start:i]
            is_negated = any(neg in NEGATION_TERMS for neg in preceding)

            if word in POSITIVE_TERMS:
                if is_negated:
                    neg_score += 1.2
                else:
                    pos_score += 1.0
            elif word in NEGATIVE_TERMS:
                if is_negated:
                    pos_score += 1.0
                else:
                    neg_score += 1.2

        if pos_score > neg_score:
            confidence = min(0.98, 0.65 + (pos_score - neg_score) * 0.12)
            return "Positive", round(confidence, 3)
        elif neg_score > pos_score:
            confidence = min(0.98, 0.65 + (neg_score - pos_score) * 0.12)
            return "Negative", round(confidence, 3)
        else:
            return "Neutral", 0.60

    def predict_aspect_sentiment(self, aspect: str, evidence_text: str) -> Tuple[str, float]:
        """
        Predicts sentiment for a detected aspect.
        Uses the trained TF-IDF hybrid classifier when available, falling back gracefully to context valence.
        """
        lex_label, lex_conf = self._lexical_sentiment_score(evidence_text)
        # Feature text combining aspect category, rule-prior token, and local clause
        feature_text = f"[{aspect}] __POL_{lex_label.upper()}__ {evidence_text}"

        if self.is_trained and self.vectorizer and self.classifier:
            try:
                x_vec = self.vectorizer.transform([feature_text])
                probs = self.classifier.predict_proba(x_vec)[0]
                classes = list(self.classifier.classes_)
                best_idx = int(probs.argmax())
                pred_label = str(classes[best_idx])
                conf = float(probs[best_idx])

                # If model is uncertain (low confidence < 0.45), blend with lexical valence
                if conf < 0.45:
                    return lex_label, lex_conf

                return pred_label, round(conf, 3)
            except Exception as exc:
                logger.debug(f"Classifier inference fallback: {exc}")

        # Rule/lexical baseline fallback
        return lex_label, lex_conf

    def analyze_text(self, text: str) -> ABSAPredictResponse:
        """
        End-to-end ABSA analysis:
          1. Detects which of the 5 aspects are mentioned.
          2. Predicts aspect-level sentiment for each.
          3. Returns structured ABSAPredictResponse.
        """
        if not text or not text.strip():
            return ABSAPredictResponse(
                text="",
                detected_aspects=[],
                aspects_count=0,
                model_version=MODEL_VERSION,
                has_aspects=False,
            )

        detected = self.detect_aspects(text)
        aspect_results: List[AspectSentimentResult] = []

        for aspect_name, evidence in detected:
            sentiment, confidence = self.predict_aspect_sentiment(aspect_name, evidence)
            aspect_results.append(
                AspectSentimentResult(
                    aspect=aspect_name,
                    sentiment=sentiment,
                    confidence=confidence,
                    evidence_text=evidence,
                )
            )

        return ABSAPredictResponse(
            text=text,
            detected_aspects=aspect_results,
            aspects_count=len(aspect_results),
            model_version=MODEL_VERSION,
            has_aspects=len(aspect_results) > 0,
        )

    def predict_text(self, text: str) -> List[AspectSentimentResult]:
        """Convenience method returning the list of detected AspectSentimentResult items."""
        return self.analyze_text(text).detected_aspects

    def predict_review(
        self,
        db: Session,
        review_id: int,
        save_prediction: bool = False,
    ) -> ABSAPredictResponse:
        """
        Analyzes an existing database review using normalized_review_text (or raw_review_text).
        Optionally persists predictions into ReviewPrediction without altering review text.
        """
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise ValueError(f"Review {review_id} not found.")

        # Use normalized_review_text as primary input, preserve raw_review_text
        text_to_analyze = review.normalized_review_text or review.raw_review_text or ""
        response = self.analyze_text(text_to_analyze)
        response.review_id = review_id

        if save_prediction and response.has_aspects:
            # Clean up prior predictions for this review if re-analyzing
            db.query(ReviewPrediction).filter(ReviewPrediction.review_id == review_id).delete()
            for aspect_res in response.detected_aspects:
                pred_row = ReviewPrediction(
                    review_id=review_id,
                    aspect=aspect_res.aspect,
                    sentiment=aspect_res.sentiment,
                    confidence=aspect_res.confidence,
                    evidence_text=aspect_res.evidence_text,
                    model_version=response.model_version,
                )
                db.add(pred_row)
            db.commit()

        return response

    def train_model(
        self,
        db: Optional[Session] = None,
        test_size: float = 0.2,
        random_state: int = 42,
        include_seed: bool = True,
        include_seed_dataset: Optional[bool] = None,
    ) -> ABSATrainResponse:
        """
        Trains and validates the ABSA sentiment classifier using eligible annotated data.
        Combines verified database annotations with the gold seed benchmark.
        """
        dataset: List[Dict[str, Any]] = []

        should_include_seed = include_seed if include_seed_dataset is None else include_seed_dataset
        # 1. Include curated seed benchmark if requested
        if should_include_seed:
            dataset.extend(SEED_BENCHMARK_DATA)

        # 2. Extract verified annotations from database
        if db is not None:
            db_annots = (
                db.query(ReviewAnnotation, Review.normalized_review_text, Review.raw_review_text)
                .join(Review, ReviewAnnotation.review_id == Review.id)
                .filter(ReviewAnnotation.status == "VERIFIED")
                .all()
            )
            for annot, norm_txt, raw_txt in db_annots:
                txt = norm_txt or raw_txt
                if txt and annot.aspect in ASPECTS_LIST and annot.sentiment in SENTIMENTS_LIST:
                    dataset.append({
                        "text": txt,
                        "aspect": annot.aspect,
                        "sentiment": annot.sentiment,
                    })

        if len(dataset) < 10:
            raise ValueError(f"Insufficient annotated training samples ({len(dataset)} found). Minimum 10 required.")

        # Prepare X and y with hybrid contextual tokens
        X_texts: List[str] = [
            f"[{item['aspect']}] __POL_{self._lexical_sentiment_score(item['text'])[0].upper()}__ {item['text']}"
            for item in dataset
        ]
        y_labels: List[str] = [item["sentiment"] for item in dataset]

        # Train / Test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_texts,
            y_labels,
            test_size=test_size,
            random_state=random_state,
            stratify=y_labels if len(set(y_labels)) > 1 else None,
        )

        # Feature Extraction: TF-IDF with unigrams and bigrams
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=1500,
            sublinear_tf=True,
            token_pattern=r"\b[a-zA-Z0-9_\-]+\b",
        )
        X_train_vec = vectorizer.fit_transform(X_train)
        X_test_vec = vectorizer.transform(X_test)

        # Classifier: Balanced Multinomial Logistic Regression
        classifier = LogisticRegression(
            class_weight="balanced",
            C=2.0,
            max_iter=500,
            random_state=random_state,
        )
        classifier.fit(X_train_vec, y_train)

        # Evaluation on held-out test split
        y_pred = classifier.predict(X_test_vec)
        acc = float(accuracy_score(y_test, y_pred))

        # Precision, Recall, F1
        p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
            y_test, y_pred, average="macro", zero_division=0
        )

        # Per-class metrics
        classes = sorted(list(set(y_labels)))
        p_class, r_class, f1_class, support = precision_recall_fscore_support(
            y_test, y_pred, labels=classes, zero_division=0
        )

        per_class_metrics: Dict[str, Any] = {}
        for c, p, r, f, s in zip(classes, p_class, r_class, f1_class, support):
            per_class_metrics[c] = {
                "precision": round(float(p), 3),
                "recall": round(float(r), 3),
                "f1_score": round(float(f), 3),
                "support": int(s),
            }

        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred, labels=classes)
        confusion_data = {
            "classes": classes,
            "matrix": cm.tolist(),
        }

        # Aspect Coverage Metrics
        aspect_counts = {asp: sum(1 for item in dataset if item["aspect"] == asp) for asp in ASPECTS_LIST}

        metrics_payload = {
            "model_version": MODEL_VERSION,
            "test_samples_count": len(y_test),
            "training_samples_count": len(X_train),
            "total_samples": len(dataset),
            "overall_accuracy": round(acc, 3),
            "overall_macro_f1": round(float(f1_macro), 3),
            "sentiment_classification_metrics": {
                "macro_precision": round(float(p_macro), 3),
                "macro_recall": round(float(r_macro), 3),
                "macro_f1": round(float(f1_macro), 3),
            },
            "per_class_sentiment_metrics": per_class_metrics,
            "confusion_matrix": confusion_data,
            "aspect_coverage": aspect_counts,
            "data_split_info": f"Train: {len(X_train)} samples, Test: {len(X_test)} samples ({int(test_size*100)}% held-out)",
            "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Update in-memory state and save to disk
        self.vectorizer = vectorizer
        self.classifier = classifier
        self.save_model(metrics_payload)

        return ABSATrainResponse(
            status="success",
            message=f"Model successfully trained on {len(X_train)} samples and evaluated on {len(X_test)} held-out samples.",
            model_version=MODEL_VERSION,
            training_samples=len(X_train),
            test_samples=len(X_test),
            sentiment_metrics=per_class_metrics,
            aspect_metrics=aspect_counts,
            overall_macro_f1=round(float(f1_macro), 3),
            overall_accuracy=round(acc, 3),
        )

    def get_metrics(self) -> ABSAMetricsResponse:
        """Returns loaded evaluation metrics for held-out test evaluation."""
        if not self.metadata:
            return ABSAMetricsResponse(has_metrics=False)

        return ABSAMetricsResponse(
            has_metrics=True,
            model_version=self.metadata.get("model_version"),
            test_samples_count=self.metadata.get("test_samples_count"),
            aspect_detection_metrics=self.metadata.get("aspect_coverage"),
            sentiment_classification_metrics=self.metadata.get("sentiment_classification_metrics"),
            per_class_sentiment_metrics=self.metadata.get("per_class_sentiment_metrics"),
            confusion_matrix=self.metadata.get("confusion_matrix"),
            last_evaluated_at=datetime.fromisoformat(self.metadata["last_evaluated_at"]) if "last_evaluated_at" in self.metadata else None,
            data_split_info=self.metadata.get("data_split_info"),
        )

    def get_status(self, db: Optional[Session] = None) -> ABSAModelStatus:
        """Returns model deployment, training readiness, and annotation counts."""
        verified_count = 0
        total_count = 0
        if db is not None:
            verified_count = db.query(ReviewAnnotation).filter(ReviewAnnotation.status == "VERIFIED").count()
            total_count = db.query(ReviewAnnotation).count()

        last_trained = None
        if self.metadata and "last_evaluated_at" in self.metadata:
            try:
                last_trained = datetime.fromisoformat(self.metadata["last_evaluated_at"])
            except Exception:
                pass

        return ABSAModelStatus(
            model_name="SmartReview Aspect-Based Sentiment Analyzer",
            model_version=MODEL_VERSION,
            is_trained=self.is_trained,
            artifacts_exist=VECTORIZER_PATH.exists() and CLASSIFIER_PATH.exists(),
            verified_annotations_count=verified_count,
            total_annotations_count=total_count,
            last_trained_at=last_trained,
        )

    # Alias train to train_model for convenience
    train = train_model


# Global singleton engine instance
absa_engine = ABSAEngine()
