import argparse
import asyncio
import logging
import random
from datetime import datetime
from typing import Any

from app.core.logging import setup_logging
from app.core.mongodb import get_mongodb_db, init_mongodb
from app.services.mongodb_report import MongoDBReportService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=20)
    return parser.parse_args()


def _shallow_equal(a: Any, b: Any) -> bool:
    return a == b


async def _run(sample_size: int) -> int:
    logger = logging.getLogger("app.verify")
    db = get_mongodb_db()
    raw = db[MongoDBReportService.COLLECTION_NAME]
    summaries = db[MongoDBReportService.SUMMARY_COLLECTION_NAME]

    total = await raw.count_documents({})
    if total == 0:
        logger.info("no_raw_reports")
        return 0

    sample_size = min(sample_size, total)
    skips = sorted(random.sample(range(total), sample_size))

    mismatches = 0
    checked = 0
    for skip in skips:
        doc = await raw.find({}).skip(skip).limit(1).to_list(length=1)
        if not doc:
            continue
        doc = doc[0]
        execution_id = doc.get("execution_id")
        if not execution_id:
            continue
        derived = await summaries.find_one({"_id": execution_id})
        if not derived:
            mismatches += 1
            logger.warning("missing_summary", extra={"execution_id": execution_id})
            continue

        recomputed_metrics = MongoDBReportService._extract_metrics(doc.get("report") or {})
        recomputed_summary = MongoDBReportService._extract_summary(doc.get("report") or {})

        stored_metrics = (derived.get("metrics") or {})
        stored_summary = (derived.get("summary") or {})

        ok = _shallow_equal(recomputed_summary, stored_summary) and _shallow_equal(
            recomputed_metrics, stored_metrics
        )
        checked += 1
        if not ok:
            mismatches += 1
            logger.warning(
                "summary_mismatch",
                extra={
                    "execution_id": execution_id,
                    "report_id": str(doc.get("_id")),
                    "created_at": (doc.get("created_at") or datetime.utcnow()).isoformat(),
                },
            )

    logger.info("verify_done", extra={"checked": checked, "mismatches": mismatches, "sample_size": sample_size})
    return 0 if mismatches == 0 else 2


def main() -> int:
    setup_logging()
    init_mongodb()
    args = _parse_args()
    return asyncio.run(_run(args.sample))


if __name__ == "__main__":
    raise SystemExit(main())

