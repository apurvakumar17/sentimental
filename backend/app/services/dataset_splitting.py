import random
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict

logger = logging.getLogger("smartreview.dataset_splitting")


def split_prepared_dataset(
    records: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Splits prepared dataset records into train, validation, and test sets with strict safeguards:
    - Verifies ratio sum equals 1.0 (within floating point margin)
    - Deterministic and reproducible using the provided random_seed
    - Prevents data leakage by grouping identical review texts / content hashes into the same split
    - Preserves product_id and review_id traceability
    - Emits clear notice that records are unannotated scaffolding, not ready for supervised training.
    """
    total_ratio = train_ratio + val_ratio + test_ratio
    if abs(total_ratio - 1.0) > 1e-4:
        raise ValueError(f"Split ratios must sum to 1.0 (got {total_ratio:.4f})")

    if not records:
        return {
            "notice": "NOTICE: Dataset prepared and split for future ABSA annotation. Not currently labeled for supervised training.",
            "total_records": 0,
            "train": [],
            "val": [],
            "test": [],
            "split_ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
            "random_seed": random_seed
        }

    # Group records by (product_id, normalized_text.lower()) to prevent data leakage across splits
    groups = defaultdict(list)
    for rec in records:
        prod_id = rec.get("product_id", 0)
        text = (rec.get("normalized_review_text") or rec.get("raw_review_text") or "").strip().lower()
        key = f"{prod_id}:{text}"
        groups[key].append(rec)

    group_keys = sorted(groups.keys()) # deterministic sorting before shuffle
    rng = random.Random(random_seed)
    rng.shuffle(group_keys)

    total_groups = len(group_keys)
    train_end = int(total_groups * train_ratio)
    val_end = train_end + int(total_groups * val_ratio)

    train_records = []
    val_records = []
    test_records = []

    for idx, key in enumerate(group_keys):
        cluster = groups[key]
        if idx < train_end:
            for item in cluster:
                tagged = dict(item)
                tagged["split"] = "train"
                train_records.append(tagged)
        elif idx < val_end:
            for item in cluster:
                tagged = dict(item)
                tagged["split"] = "val"
                val_records.append(tagged)
        else:
            for item in cluster:
                tagged = dict(item)
                tagged["split"] = "test"
                test_records.append(tagged)

    logger.info(
        f"Split {len(records)} records ({total_groups} distinct clusters) -> "
        f"Train: {len(train_records)}, Val: {len(val_records)}, Test: {len(test_records)}"
    )

    return {
        "notice": "NOTICE: Dataset prepared and split for future ABSA annotation. Not currently labeled for supervised training.",
        "total_records": len(records),
        "split_counts": {
            "train": len(train_records),
            "val": len(val_records),
            "test": len(test_records)
        },
        "split_ratios": {
            "train": train_ratio,
            "val": val_ratio,
            "test": test_ratio
        },
        "random_seed": random_seed,
        "train": train_records,
        "val": val_records,
        "test": test_records
    }
