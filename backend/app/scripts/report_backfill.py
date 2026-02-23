import argparse
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from app.core.logging import setup_logging
from app.core.mongodb import get_mongodb_db, init_mongodb
from app.services.mongodb_report import MongoDBReportService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--since", type=str, default=None, help="ISO time, UTC (e.g. 2026-02-01T00:00:00)")
    parser.add_argument("--until", type=str, default=None, help="ISO time, UTC")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


async def _run(args: argparse.Namespace) -> int:
    logger = logging.getLogger("app.backfill")
    db = get_mongodb_db()
    raw = db[MongoDBReportService.COLLECTION_NAME]

    match: dict[str, Any] = {}
    if args.days is not None:
        match["created_at"] = {"$gte": datetime.utcnow() - timedelta(days=args.days)}
    if args.since:
        match.setdefault("created_at", {})
        match["created_at"]["$gte"] = _parse_iso(args.since)
    if args.until:
        match.setdefault("created_at", {})
        match["created_at"]["$lte"] = _parse_iso(args.until)

    cursor = raw.find(match).sort("created_at", -1)
    if args.limit is not None:
        cursor = cursor.limit(args.limit)

    processed = 0
    upserted = 0
    async for doc in cursor:
        processed += 1
        report_id = str(doc.get("_id"))
        execution_id = doc.get("execution_id")
        apifox_collection_id = doc.get("apifox_collection_id", "")
        project_name = doc.get("project_name", "")
        environment = doc.get("environment", "")
        created_at = doc.get("created_at") or datetime.utcnow()
        report_data = doc.get("report") or {}

        if not execution_id:
            logger.warning("skip_missing_execution_id", extra={"report_id": report_id})
            continue

        if args.dry_run:
            logger.info("would_upsert_derived", extra={"execution_id": execution_id, "report_id": report_id})
            continue

        await MongoDBReportService.upsert_derived(
            report_id=report_id,
            execution_id=execution_id,
            apifox_collection_id=apifox_collection_id,
            project_name=project_name,
            environment=environment,
            created_at=created_at,
            report_data=report_data,
        )
        upserted += 1

        if processed % 100 == 0:
            logger.info("backfill_progress", extra={"processed": processed, "upserted": upserted})

    logger.info("backfill_done", extra={"processed": processed, "upserted": upserted, "dry_run": args.dry_run})
    return 0


def main() -> int:
    setup_logging()
    init_mongodb()
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())

