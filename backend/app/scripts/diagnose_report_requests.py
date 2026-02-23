import asyncio
import logging

from app.core.mongodb import get_mongodb_db, init_mongodb
from app.services.mongodb_report import MongoDBReportService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_mongodb()
    db = get_mongodb_db()

    counts = {
        "test_reports": await db[MongoDBReportService.COLLECTION_NAME].count_documents({}),
        "report_summaries": await db[MongoDBReportService.SUMMARY_COLLECTION_NAME].count_documents({}),
        "report_requests": await db[MongoDBReportService.REQUESTS_COLLECTION_NAME].count_documents({}),
        "report_failures": await db[MongoDBReportService.FAILURES_COLLECTION_NAME].count_documents({}),
    }
    logging.getLogger("app.diagnose").info("counts=%s", counts)


if __name__ == "__main__":
    asyncio.run(main())

