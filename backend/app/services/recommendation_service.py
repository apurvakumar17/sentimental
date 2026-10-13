import logging
import math
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.review_import_metadata import ReviewImportMetadata
from backend.app.models.absa import ReviewPrediction, ReviewAnnotation
from backend.app.services.absa_service import absa_engine, ASPECTS_LIST
from backend.app.schemas.recommendation import (
    AspectDefinition,
    AspectScoreItem,
    ProductRecommendationItem,
    RecommendationRequest,
    RecommendationResponse,
    ProductComparisonItem,
    ComparisonResponse,
    ProductScoreDetailResponse,
    ProductSummaryItem,
)

logger = logging.getLogger("smartreview.recommendations")

# Academic Bayesian Credibility Parameters
# Damps small-sample volatility towards prior mean (50.0 / 100)
BAYESIAN_PRIOR_WEIGHT = 3.0
BAYESIAN_PRIOR_MEAN = 50.0

ASPECT_META: Dict[str, Dict[str, Any]] = {
    "Battery": {
        "description": "Battery longevity, charging rate, daily endurance, and screen-on time.",
        "keywords": ["battery", "charging", "drain", "backup", "mAh", "endurance", "fast charge"],
        "default_weight": 2.0,
    },
    "Camera": {
        "description": "Image clarity, low-light photography, video stabilization, and sensor performance.",
        "keywords": ["camera", "photos", "sensor", "lens", "portrait", "night mode", "zoom"],
        "default_weight": 2.5,
    },
    "Performance": {
        "description": "Processor speed, responsiveness, gaming capabilities, and thermal throttling.",
        "keywords": ["processor", "speed", "gaming", "lag", "fps", "chipset", "snapdragon", "ram"],
        "default_weight": 2.5,
    },
    "Design": {
        "description": "Chassis build quality, ergonomic hand feel, weight, finish, and materials.",
        "keywords": ["design", "build", "finish", "titanium", "glass back", "ergonomics", "lightweight"],
        "default_weight": 1.5,
    },
    "Display": {
        "description": "Screen resolution, AMOLED/OLED color accuracy, refresh rate, and outdoor visibility.",
        "keywords": ["display", "screen", "AMOLED", "OLED", "120Hz", "brightness", "sharpness"],
        "default_weight": 1.8,
    },
}


class RecommendationEngine:
    """
    Aspect-Based Smartphone Recommendation & Comparison Engine.
    Combines budget constraints, brand preferences, user aspect priorities,
    and Bayesian-smoothed aspect scores derived from verified annotations
    and stored ABSA review predictions.
    """

    def get_aspect_definitions(self) -> List[AspectDefinition]:
        """Returns metadata and default weights for all supported smartphone aspects."""
        results = []
        for aspect, meta in ASPECT_META.items():
            results.append(
                AspectDefinition(
                    aspect=aspect,
                    description=meta["description"],
                    keywords=meta["keywords"],
                    default_weight=meta["default_weight"],
                )
            )
        return results

    def get_product_prices_map(self, db: Session, product_ids: Optional[List[int]] = None) -> Dict[int, float]:
        """
        Calculates the representative USD price for products by averaging
        known price_usd fields from imported Kaggle review metadata.
        """
        query = (
            db.query(
                Review.product_id,
                func.avg(ReviewImportMetadata.price_usd).label("avg_price"),
            )
            .join(ReviewImportMetadata, Review.id == ReviewImportMetadata.review_id)
            .filter(ReviewImportMetadata.price_usd.isnot(None))
        )
        if product_ids:
            query = query.filter(Review.product_id.in_(product_ids))

        rows = query.group_by(Review.product_id).all()
        return {r[0]: round(float(r[1]), 2) for r in rows if r[1] is not None}

    def compute_aspect_scores_for_products(
        self,
        db: Session,
        product_ids: List[int],
    ) -> Dict[int, Dict[str, AspectScoreItem]]:
        """
        Aggregates aspect evidence from stored predictions and verified annotations.
        Deduplicates by (review_id, aspect) and applies Bayesian smoothing.
        Returns a mapping of {product_id: {aspect_name: AspectScoreItem}}.
        """
        if not product_ids:
            return {}

        # 1. Fetch Verified Human Annotations for target products
        # Annotations carry weight 1.5
        annot_rows = (
            db.query(
                Review.product_id,
                ReviewAnnotation.review_id,
                ReviewAnnotation.aspect,
                ReviewAnnotation.sentiment,
            )
            .join(Review, ReviewAnnotation.review_id == Review.id)
            .filter(
                Review.product_id.in_(product_ids),
                ReviewAnnotation.status == "VERIFIED",
                ReviewAnnotation.aspect.in_(ASPECTS_LIST),
            )
            .all()
        )

        # 2. Fetch Stored ABSA Model Predictions for target products
        # Predictions carry weight = 1.0 * confidence
        pred_rows = (
            db.query(
                Review.product_id,
                ReviewPrediction.review_id,
                ReviewPrediction.aspect,
                ReviewPrediction.sentiment,
                ReviewPrediction.confidence,
            )
            .join(Review, ReviewPrediction.review_id == Review.id)
            .filter(
                Review.product_id.in_(product_ids),
                ReviewPrediction.aspect.in_(ASPECTS_LIST),
            )
            .all()
        )

        # Structure: product_id -> aspect -> review_id -> (sentiment, weight)
        evidence_by_review: Dict[int, Dict[str, Dict[int, Tuple[str, float]]]] = defaultdict(
            lambda: defaultdict(dict)
        )

        # Insert model predictions first
        for pid, rid, asp, sent, conf in pred_rows:
            weight = max(0.5, min(1.0, float(conf or 0.8)))
            evidence_by_review[pid][asp][rid] = (sent, weight)

        # Overwrite with verified annotations if present (higher precedence & weight)
        for pid, rid, asp, sent in annot_rows:
            evidence_by_review[pid][asp][rid] = (sent, 1.5)

        # Compute smoothed aspect scores per product
        result: Dict[int, Dict[str, AspectScoreItem]] = {}

        for pid in product_ids:
            result[pid] = {}
            for asp in ASPECTS_LIST:
                rev_records = evidence_by_review[pid].get(asp, {})
                evidence_count = len(rev_records)

                if evidence_count == 0:
                    result[pid][asp] = AspectScoreItem(
                        aspect=asp,
                        score=None,
                        is_available=False,
                        evidence_count=0,
                        positive_count=0,
                        neutral_count=0,
                        negative_count=0,
                        raw_sentiment_ratio=None,
                        confidence_weighted_evidence=0.0,
                    )
                    continue

                pos_count = sum(1 for s, _ in rev_records.values() if s == "Positive")
                neu_count = sum(1 for s, _ in rev_records.values() if s == "Neutral")
                neg_count = sum(1 for s, _ in rev_records.values() if s == "Negative")

                w_pos = sum(w for s, w in rev_records.values() if s == "Positive")
                w_neu = sum(w for s, w in rev_records.values() if s == "Neutral")
                w_neg = sum(w for s, w in rev_records.values() if s == "Negative")

                n_eff = w_pos + w_neu + w_neg

                # Raw positive ratio
                raw_ratio = (w_pos + 0.5 * w_neu) / n_eff if n_eff > 0 else 0.5

                # Bayesian shrinkage towards 50.0 prior:
                # Score = ((w_pos + 0.5 * w_neu) * 100 + m * mu_0) / (n_eff + m)
                smoothed_score = (
                    (w_pos + 0.5 * w_neu) * 100.0 + BAYESIAN_PRIOR_WEIGHT * BAYESIAN_PRIOR_MEAN
                ) / (n_eff + BAYESIAN_PRIOR_WEIGHT)

                result[pid][asp] = AspectScoreItem(
                    aspect=asp,
                    score=round(float(smoothed_score), 1),
                    is_available=True,
                    evidence_count=evidence_count,
                    positive_count=pos_count,
                    neutral_count=neu_count,
                    negative_count=neg_count,
                    raw_sentiment_ratio=round(float(raw_ratio), 3),
                    confidence_weighted_evidence=round(float(n_eff), 2),
                )

        return result

    def get_eligible_products(
        self,
        db: Session,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        brands: Optional[List[str]] = None,
    ) -> List[Tuple[Product, Optional[float], int]]:
        """
        Queries products filtered by brand preferences and budget range.
        Returns List of (Product, price_usd, total_reviews_count).
        """
        prices_map = self.get_product_prices_map(db)

        # Review counts per product
        rev_count_rows = (
            db.query(Review.product_id, func.count(Review.id))
            .group_by(Review.product_id)
            .all()
        )
        rev_counts = {r[0]: int(r[1]) for r in rev_count_rows}

        products_query = db.query(Product)

        # Filter brands if requested
        if brands:
            clean_brands = [b.strip() for b in brands if b.strip()]
            if clean_brands:
                brand_filters = [Product.brand.ilike(f"%{b}%") for b in clean_brands]
                products_query = products_query.filter(or_(*brand_filters))

        all_products = products_query.all()
        eligible = []

        for prod in all_products:
            price = prices_map.get(prod.id)
            total_revs = rev_counts.get(prod.id, 0)

            # Check budget constraints
            if min_price is not None:
                if price is None or price < min_price:
                    continue
            if max_price is not None:
                if price is None or price > max_price:
                    continue

            eligible.append((prod, price, total_revs))

        return eligible

    def recommend(
        self,
        db: Session,
        request: RecommendationRequest,
    ) -> RecommendationResponse:
        """
        Calculates multi-criteria aspect-based recommendations according to user preferences.
        Ranks products by weighted aspect performance, evidence reliability, and budget fit.
        """
        # Validate selected priorities
        selected_priorities = [
            p.strip().capitalize() for p in request.priorities if p.strip().capitalize() in ASPECTS_LIST
        ]
        if not selected_priorities:
            selected_priorities = ["Camera", "Battery", "Performance"]

        # Determine numerical weights
        # If user supplied custom weights, use them; otherwise use rank-order default weights
        weights_map: Dict[str, float] = {}
        if request.priority_weights:
            for asp, w in request.priority_weights.items():
                clean_asp = asp.strip().capitalize()
                if clean_asp in selected_priorities and w > 0:
                    weights_map[clean_asp] = float(w)

        # Assign rank-order defaults for any unset priority (emphasizing top priorities)
        rank_multipliers = [5.0, 2.5, 1.5, 1.0, 0.5]
        for idx, asp in enumerate(selected_priorities):
            if asp not in weights_map:
                mult = rank_multipliers[idx] if idx < len(rank_multipliers) else 0.5
                weights_map[asp] = mult

        # Fetch eligible products matching budget and brands
        eligible = self.get_eligible_products(
            db,
            min_price=request.min_price,
            max_price=request.max_price,
            brands=request.brands,
        )

        if not eligible:
            budget_str = f"${request.min_price or 0} – ${request.max_price or '∞'}"
            brand_str = ", ".join(request.brands) if request.brands else "All Brands"
            return RecommendationResponse(
                total_eligible_products=0,
                matched_products_count=0,
                applied_budget_filter=budget_str if (request.min_price or request.max_price) else None,
                applied_brand_filter=request.brands,
                priorities_evaluated=selected_priorities,
                recommendations=[],
                empty_state_reason=f"No smartphones found matching budget {budget_str} and brand preferences: {brand_str}.",
            )

        product_ids = [p.id for p, _, _ in eligible]
        aspect_scores_by_prod = self.compute_aspect_scores_for_products(db, product_ids)

        # Tally predictions count for each product
        pred_counts_rows = (
            db.query(Review.product_id, func.count(ReviewPrediction.id))
            .join(ReviewPrediction, Review.id == ReviewPrediction.review_id)
            .filter(Review.product_id.in_(product_ids))
            .group_by(Review.product_id)
            .all()
        )
        pred_counts = {r[0]: int(r[1]) for r in pred_counts_rows}

        ranked_candidates: List[Tuple[float, float, int, ProductRecommendationItem]] = []

        for prod, price, total_revs in eligible:
            asp_scores = aspect_scores_by_prod.get(prod.id, {})
            p_preds = pred_counts.get(prod.id, 0)

            # Check min evidence filter
            total_evidence_across_aspects = sum(
                asp_item.evidence_count for asp_item in asp_scores.values()
            )
            if request.min_evidence_count and total_evidence_across_aspects < request.min_evidence_count:
                # If product doesn't meet minimum review evidence, exclude unless no other products exist
                continue

            # Calculate weighted overall score
            eval_weights_sum = 0.0
            eval_scores_sum = 0.0
            eval_aspects_count = 0

            for asp in selected_priorities:
                asp_item = asp_scores.get(asp)
                if asp_item and asp_item.is_available and asp_item.score is not None:
                    w = weights_map.get(asp, 1.0)
                    eval_scores_sum += asp_item.score * w
                    eval_weights_sum += w
                    eval_aspects_count += 1

            coverage_ratio = (
                eval_aspects_count / len(selected_priorities) if selected_priorities else 0.0
            )

            overall_score = (
                round(eval_scores_sum / eval_weights_sum, 1) if eval_weights_sum > 0 else None
            )

            # Determine Strengths (Score >= 68 with evidence >= 2)
            strengths = []
            for asp, item in asp_scores.items():
                if item.is_available and item.score is not None and item.score >= 68.0 and item.evidence_count >= 2:
                    strengths.append(f"{asp} ({item.score}/100)")

            # Determine Weaknesses (Score <= 45 with evidence >= 2)
            weaknesses = []
            for asp, item in asp_scores.items():
                if item.is_available and item.score is not None and item.score <= 45.0 and item.evidence_count >= 2:
                    weaknesses.append(f"{asp} ({item.score}/100)")

            # Generate personalized explanation
            explanation_parts = []
            if overall_score is not None:
                top_priority = selected_priorities[0]
                top_item = asp_scores.get(top_priority)
                if top_item and top_item.is_available and top_item.score is not None:
                    explanation_parts.append(
                        f"Performs strongly in your #1 priority {top_priority} with an aspect score of {top_item.score}/100 based on {top_item.evidence_count} reviews."
                    )
                else:
                    explanation_parts.append(
                        f"Achieved an overall recommendation score of {overall_score}/100 across evaluated priorities."
                    )
            else:
                explanation_parts.append(
                    "Currently has limited aspect-level review evidence for your selected priorities."
                )

            data_limitations = []
            missing_priorities = [
                asp for asp in selected_priorities
                if not (asp_scores.get(asp) and asp_scores[asp].is_available)
            ]
            if missing_priorities:
                data_limitations.append(
                    f"Insufficient review evidence for priority aspects: {', '.join(missing_priorities)}."
                )
            if total_revs < 10:
                data_limitations.append(
                    f"Sample size is low ({total_revs} total reviews collected)."
                )

            rec_item = ProductRecommendationItem(
                rank=0,  # updated after sort
                product_id=prod.id,
                product_name=prod.name,
                brand=prod.brand,
                price_usd=price,
                price_display=f"${price:.2f}" if price else "Price Unavailable",
                overall_score=overall_score,
                coverage_ratio=round(coverage_ratio, 2),
                aspect_scores=asp_scores,
                total_reviews_count=total_revs,
                total_predictions_count=p_preds,
                strengths=strengths,
                weaknesses=weaknesses,
                explanation=" ".join(explanation_parts),
                data_limitations=data_limitations,
            )

            # Sort key:
            # 1. overall_score (None treated as -1)
            # 2. coverage_ratio
            # 3. total_evidence_across_aspects
            score_key = overall_score if overall_score is not None else -1.0
            ranked_candidates.append(
                (score_key, coverage_ratio, total_evidence_across_aspects, rec_item)
            )

        # Sort descending by score, coverage, and evidence
        ranked_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

        final_recommendations: List[ProductRecommendationItem] = []
        for rank_idx, (_, _, _, item) in enumerate(ranked_candidates[: request.limit], start=1):
            item.rank = rank_idx
            final_recommendations.append(item)

        budget_str = None
        if request.min_price or request.max_price:
            budget_str = f"${request.min_price or 0} – ${request.max_price or '∞'}"

        return RecommendationResponse(
            total_eligible_products=len(eligible),
            matched_products_count=len(final_recommendations),
            applied_budget_filter=budget_str,
            applied_brand_filter=request.brands,
            priorities_evaluated=selected_priorities,
            recommendations=final_recommendations,
            empty_state_reason=None if final_recommendations else "No smartphones met the minimum review evidence criteria within the selected filters.",
        )

    def compare(self, db: Session, product_ids: List[int]) -> ComparisonResponse:
        """
        Compares 2 to 5 smartphones side by side across pricing, aspect scores,
        sentiment breakdown, and evidence quantity.
        """
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        if len(products) < 2:
            raise ValueError("Product comparison requires at least 2 distinct existing products.")

        prices_map = self.get_product_prices_map(db, product_ids)
        aspect_scores_by_prod = self.compute_aspect_scores_for_products(db, product_ids)

        rev_count_rows = (
            db.query(Review.product_id, func.count(Review.id))
            .filter(Review.product_id.in_(product_ids))
            .group_by(Review.product_id)
            .all()
        )
        rev_counts = {r[0]: int(r[1]) for r in rev_count_rows}

        comparison_items: List[ProductComparisonItem] = []
        best_aspect_performer: Dict[str, Tuple[Optional[str], float]] = {
            asp: (None, -1.0) for asp in ASPECTS_LIST
        }

        for prod in products:
            price = prices_map.get(prod.id)
            asp_scores = aspect_scores_by_prod.get(prod.id, {})
            total_revs = rev_counts.get(prod.id, 0)
            total_evidence = sum(a.evidence_count for a in asp_scores.values())

            # Mean score across all available aspects
            avail_scores = [a.score for a in asp_scores.values() if a.is_available and a.score is not None]
            overall = round(sum(avail_scores) / len(avail_scores), 1) if avail_scores else None

            # Track winner per aspect
            for asp, a_item in asp_scores.items():
                if a_item.is_available and a_item.score is not None:
                    curr_winner, curr_best = best_aspect_performer[asp]
                    if a_item.score > curr_best:
                        best_aspect_performer[asp] = (prod.name, a_item.score)

            strengths = [
                f"{asp} ({a.score}/100)"
                for asp, a in asp_scores.items()
                if a.is_available and a.score is not None and a.score >= 68.0 and a.evidence_count >= 2
            ]
            weaknesses = [
                f"{asp} ({a.score}/100)"
                for asp, a in asp_scores.items()
                if a.is_available and a.score is not None and a.score <= 45.0 and a.evidence_count >= 2
            ]

            comparison_items.append(
                ProductComparisonItem(
                    product_id=prod.id,
                    product_name=prod.name,
                    brand=prod.brand,
                    price_usd=price,
                    price_display=f"${price:.2f}" if price else "Price Unavailable",
                    overall_score=overall,
                    aspect_scores=asp_scores,
                    total_reviews_count=total_revs,
                    total_evidence_count=total_evidence,
                    strengths=strengths,
                    weaknesses=weaknesses,
                )
            )

        # Summary narrative
        winner_phrases = []
        for asp, (winner_name, score) in best_aspect_performer.items():
            if winner_name and score > 0:
                winner_phrases.append(f"{winner_name} leads in {asp} ({score}/100)")

        summary = (
            "; ".join(winner_phrases[:3]) + "."
            if winner_phrases
            else "Comparison completed with limited aspect differentiation."
        )

        winners_dict = {
            asp: (winner_name if score > 0 else None)
            for asp, (winner_name, score) in best_aspect_performer.items()
        }

        return ComparisonResponse(
            products=comparison_items,
            aspect_winners=winners_dict,
            summary=summary,
        )

    def get_product_score_detail(self, db: Session, product_id: int) -> ProductScoreDetailResponse:
        """
        Retrieves detailed aspect scoring and sample evidence quotes for a single smartphone.
        """
        prod = db.query(Product).filter(Product.id == product_id).first()
        if not prod:
            raise ValueError(f"Product with ID {product_id} not found.")

        prices_map = self.get_product_prices_map(db, [product_id])
        price = prices_map.get(product_id)

        aspect_scores_by_prod = self.compute_aspect_scores_for_products(db, [product_id])
        asp_scores = aspect_scores_by_prod.get(product_id, {})

        total_revs = db.query(Review).filter(Review.product_id == product_id).count()

        # Sample evidence snippets per aspect
        evidence_snippets: Dict[str, List[str]] = defaultdict(list)
        pred_snippets = (
            db.query(ReviewPrediction.aspect, ReviewPrediction.evidence_text)
            .join(Review, ReviewPrediction.review_id == Review.id)
            .filter(
                Review.product_id == product_id,
                ReviewPrediction.evidence_text.isnot(None),
            )
            .limit(30)
            .all()
        )
        for asp, snip in pred_snippets:
            if snip and len(evidence_snippets[asp]) < 3:
                evidence_snippets[asp].append(snip)

        strengths = [
            f"{asp} ({a.score}/100)"
            for asp, a in asp_scores.items()
            if a.is_available and a.score is not None and a.score >= 68.0 and a.evidence_count >= 2
        ]
        weaknesses = [
            f"{asp} ({a.score}/100)"
            for asp, a in asp_scores.items()
            if a.is_available and a.score is not None and a.score <= 45.0 and a.evidence_count >= 2
        ]

        return ProductScoreDetailResponse(
            product_id=prod.id,
            product_name=prod.name,
            brand=prod.brand,
            price_usd=price,
            total_reviews=total_revs,
            aspect_scores=asp_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            sample_evidence=dict(evidence_snippets),
        )

    def sync_warehouse_predictions(
        self,
        db: Session,
        limit_per_product: int = 50,
    ) -> Dict[str, Any]:
        """
        Precomputes ABSA predictions for existing warehouse reviews to ensure
        all database products possess rich, stored aspect evidence in review_predictions.
        Runs in bounded batches per product without hogging system memory.
        """
        products = db.query(Product).all()
        total_predictions_created = 0
        products_updated = 0

        for prod in products:
            # Query reviews for this product that do not yet have predictions
            unpredicted_reviews = (
                db.query(Review)
                .outerjoin(ReviewPrediction, Review.id == ReviewPrediction.review_id)
                .filter(
                    Review.product_id == prod.id,
                    ReviewPrediction.id.is_(None),
                )
                .limit(limit_per_product)
                .all()
            )

            if not unpredicted_reviews:
                continue

            products_updated += 1
            for rev in unpredicted_reviews:
                text_to_analyze = rev.normalized_review_text or rev.raw_review_text or ""
                if not text_to_analyze.strip():
                    continue

                res = absa_engine.analyze_text(text_to_analyze)
                if res.has_aspects:
                    for asp_item in res.detected_aspects:
                        pred_row = ReviewPrediction(
                            review_id=rev.id,
                            aspect=asp_item.aspect,
                            sentiment=asp_item.sentiment,
                            confidence=asp_item.confidence,
                            evidence_text=asp_item.evidence_text,
                            model_version=res.model_version,
                        )
                        db.add(pred_row)
                        total_predictions_created += 1

            db.commit()

        logger.info(
            f"Synced {total_predictions_created} predictions across {products_updated} products."
        )
        return {
            "status": "success",
            "products_processed": len(products),
            "products_updated": products_updated,
            "predictions_created": total_predictions_created,
        }


# Global singleton instance
recommendation_engine = RecommendationEngine()
