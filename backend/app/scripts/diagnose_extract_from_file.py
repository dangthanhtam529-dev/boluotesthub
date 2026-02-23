import json
import logging

from app.services.mongodb_report import MongoDBReportService


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    path = "apifox-reports-local/apifox-report-2026-02-11-11-42-02-345-0.json"
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    rows = MongoDBReportService._extract_requests(report)
    logging.getLogger("app.diagnose").info("extract_requests rows=%s", len(rows))
    if rows:
        logging.getLogger("app.diagnose").info("sample=%s", rows[0])


if __name__ == "__main__":
    main()

